import requests
from bs4 import BeautifulSoup
from lxml import etree
import os
import shutil
import re
import time
from requests.packages.urllib3.connectionpool import HTTPConnectionPool
from httplib import HTTPConnection

from multiprocessing import Process
from multiprocessing.managers import SyncManager

def get_typeid_from_url(url):
    m = re.match(".*typeid=(\d+).*", url)
    if m:
        return int(m.groups()[0])
    return -1

class Component(object):
    def __init__(self, name, type_id, amount=1):
        self.name = name
        self.type_id = type_id
        self.amount = amount
        
        self.components = {}
        
    def __str__(self):
        return "Component (" + self.name + "|" + str(self.type_id) + "): amount -> " + str(self.amount)

def get_page_data(url, return_dict):
    r = requests.get(url)
    return_dict['page'] = r.text


class ManufacturingRequirements(object):
    """
    Manufacturing requirements are accumulated and stored by this class.
    
    self.requirements = {
        <type_id>: Component,
        <type_id>: Component,
        <type_id>: Component,
        <type_id>: Component
    }
    """
    def __init__(self):
        self.requirements_filename = "requirements.txt"
        self._clear()
        
        self.job = None
        
        self.manager = SyncManager()
        self.manager.start()
        
        
    def _clear(self):
        self.requirements = {}
        
    def get_existing_type_ids(self):
        ids = []
        for component in self.requirements:
            ids.append(component.type_id)
        return ids
    
    def finish(self):
        self.save_requirements()
        
    def load_requirements(self, filename=None):
        if not filename:
            filename = self.requirements_filename
        
        self._clear()
        
        if os.path.exists(filename):
            
            f = open(filename, 'r')
            for line in f:
                parts = line.split(':')
                manufactured_component_str = parts[0].strip()
                manufactured_component_str_parts = manufactured_component_str.split('|') 
                manufactured_type_id = int(manufactured_component_str_parts[0])
                manufactured_type_name = manufactured_component_str_parts[1]
                
                manufactured_component = Component(manufactured_type_name, manufactured_type_id) 
                
                component_parts = parts[1].strip().split(' ')
                for component_str in component_parts:
                    component_str_parts = component_str.split('|')
                    component_type_id = int(component_str_parts[0])
                    component_amount = float(component_str_parts[1])
                    
                    manufactured_component.components[component_type_id] = Component("", component_type_id, component_amount)
                    
                self.requirements[manufactured_type_id] = manufactured_component
                    
            f.close()
            
    def save_requirements(self, filename=None):
        # <type_id of object to manufacture>|<name> : <type_id of requirement>|<amount> <type_id of requirement>|<amount> ...
        
        if not filename:
            filename = self.requirements_filename
        
        if os.path.exists(filename):
            backup_filename = filename + ".bak"
            if os.path.exists(backup_filename):
                os.remove(backup_filename)
                
            shutil.copy(filename, backup_filename)
        
        f = open(filename, 'w')
        
        keys = self.requirements.keys()
        keys.sort()
        
        for type_id in keys:
            component = self.requirements[type_id]
            f.write(str(component.type_id) + "|" + component.name)
            f.write(' : ')
            
            entries = component.components.keys()
            for type_id in entries:
                entry = component.components[type_id]
                f.write(str(entry.type_id) + "|" + str(entry.amount) + " ")
                
            f.write('\n')
        f.close()
        
        print "Requirement status saved."
                
    def save_page(self, page_filename, market_data):
        
        if not os.path.exists(os.path.dirname(page_filename)):
            os.mkdir(os.path.dirname(page_filename))
            
        f = open(page_filename, 'w')
        f.write(market_data)
        f.close()
    
    def get_full_requirements_dict(self, type_id):
        
        if type_id == -1:
            return None
        
        if not self.requirements.has_key(type_id):
            self.add_manufacturing_requirements(type_id)
            
        final_requirements = {}
        if type_id not in self.requirements:
            raise Exception("Requirement for " + str(type_id) + " not found!")
        
        manufactured_component = self.requirements[type_id]
        
        for component_id in manufactured_component.components.keys():
            # Check if we need to recurse:
            sub_requirements = {}
            component = manufactured_component.components[component_id]
            
            if component_id != -1:
                sub_requirements = self.get_full_requirements_dict(component_id)
                if sub_requirements:
                    # Add sub requirements
                    for sub_id in sub_requirements:
                        if sub_id in final_requirements.keys():
                            final_requirements[sub_id] += sub_requirements[sub_id] * component.amount
                        else:
                            final_requirements[sub_id] = sub_requirements[sub_id] * component.amount
                else:
                    
                    if component_id in final_requirements.keys():
                        final_requirements[component_id] += component.amount
                    else:
                        final_requirements[component_id] = component.amount
        
        return final_requirements
    
    def _get_cache_filename(self, type_id):
        page_dir = "pages"
        subdir = os.path.join(page_dir, str(type_id / 1000))
        
        if not os.path.exists(subdir):
            os.makedirs(subdir)
        
        cache_filename = os.path.join(subdir, str(type_id) + ".htm")
        return cache_filename
    
    def retry_fetch_market_data(self, markets_url, cache_filename):
        market_data = self.fetch_market_data(markets_url, cache_filename)
        
        retries = 1
        while not market_data and retries < 100:
            print "Retry #%s..." % str(retries)
            market_data = self.fetch_market_data(markets_url, cache_filename)
            if market_data:
                print "Fetched: " + str(len(market_data))
            else:
                print "Fetched nothing!"
            retries += 1
        
        return market_data
    
    def fetch_market_data(self, markets_url, cache_filename):
        print "Downloading " + markets_url
            
        return_dict = self.manager.dict()
        self.job = Process(target=get_page_data, args=(markets_url, return_dict))
        self.job.start()
        
        self.job.join(30.0)
        if self.job.is_alive():
            self.job.terminate()
        self.job = None
        
        market_data = None
        if 'page' in return_dict:
            market_data = return_dict['page']
        
        if market_data:
            self.save_page(cache_filename, market_data)
        
        time.sleep(1.0)
        
        return market_data
    
    def add_manufacturing_requirements(self, type_id):
        
        markets_url = "http://www.eve-markets.net/detail.php?typeid=%s#industry" % type_id
        cache_filename = self._get_cache_filename(type_id)
        
        market_data = None
        if not os.path.exists(cache_filename):
            market_data = self.retry_fetch_market_data(markets_url, cache_filename) 

        else:
            print "Using cache: " + cache_filename
            f = open(cache_filename, 'r')
            market_data = f.read()
            f.close()
            
            if len(market_data) == 0:
                os.remove(cache_filename)
                
                print "Bogus cache, retrying download..."
                market_data = self.retry_fetch_market_data(markets_url, cache_filename)
        
#        f = open("data//Sorry.htm", 'r')
#        market_data = f.read()
#        f.close()
        
        if not market_data:
            raise Exception("Failed download!")
            return False
        
        market_soup = BeautifulSoup(market_data)
        
        if 'Sorry' in [v.string for v in market_soup.find_all('h2')] or 'Error' in [v.string for v in market_soup.find_all('h1')]:
            # The item with this typeid does not exist!
            manufactured_component = Component("Empty", type_id)
            manufactured_component.components = {-1: Component("Empty", -1)}
            self.requirements[type_id] = manufactured_component
            return False
        
        type_name = market_soup.find_all('h1')[0].string
        
        manufactured_component = Component(type_name, type_id, 1)
        
        markets_url = "http://www.eve-markets.net/detail.php?typeid=%s#industry" % type_id
        
        for_unit_count = 1
        
        manufacturing_specified = False
        for div in market_soup.find_all('div'):
            for c in div.contents:
                if c.name == 'h4' and c.string == 'Manufacturing':
                    # This should happen only once if there is a manufacturing bit
                    
                    for sub_div in div.find_all('div'):
                        if sub_div.get('class')[0] == 'displaylist_footer_multi':
                            for_unit_count = int(sub_div.find_all('span')[0].string[10:13])
                    
                    manufacturing_specified = True
                    dl = div.find_all('dl')[0]
                    for dt in dl.find_all('dt'):
                        spans = dt.find_all('span')
                        name_span = spans[0]
                        amount_span = spans[1]
                        
                        component_name = ""
                        component_url = name_span.find_all('a')[0].get('href')
                        component_type_id = get_typeid_from_url(component_url)
                        component_amount = float(amount_span.string)
                        
                        if for_unit_count > 1:
                            component_amount = float(component_amount) / float(for_unit_count)
                        
                        manufactured_component.components[component_type_id] = Component(component_name, component_type_id, component_amount)
        
        if not manufacturing_specified:
            manufactured_component.components = {-1: Component("Empty", -1)}

        self.requirements[type_id] = manufactured_component
        
        return True
    
    def print_requirements(self):
        for component in self.requirements.keys():
            print "Base item: " + str(component)
            for type_id in self.requirements[component]:
                print " * " + str(self.requirements[component][type_id])
        
        print ""
            

if __name__ == "__main__":
    m = ManufacturingRequirements()
    
    print "Loading existing requirements"
    m.load_requirements()
    print "Done!"
    
    force = False
    
    drake = 24698
    ammo = 197
    
    start = 0
    end = 1568
    
    try:
        for type_id_to_check in range(start, end):
            if type_id_to_check not in m.requirements or force:
                try:
                    if m.add_manufacturing_requirements(type_id_to_check):
                        print "Added: " + m.requirements[type_id_to_check].name
                    else:
                        #print str(type_id_to_check) + " doesn't exist..."
                        pass
                except requests.exceptions.RequestException, e:
                    print "Request HTTP Error: " + str(e)
                
            else:
                print "Skipping type " + str(type_id_to_check) + "!"
                
            if type_id_to_check % 1000 == 0:
                m.save_requirements()
            
    except Exception, e:
        print "A problem occurred!"
        raise e
    finally:
        m.save_requirements()
        
        if m.job != None:
            m.job.terminate()
            m.job.join()
            m.job = None
        
    
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
from downloader import Downloader
from data_accumulator import DataAccumulator
from groups import Groups

def get_typeid_from_url(url):
    m = re.match(".*typeid=(\d+).*", url)
    if m:
        return int(m.groups()[0])
    return -1

def get_group_id_from_url(url):
    m = re.match(".*group=(\d+).*", url)
    if m:
        return int(m.groups()[0])
    return -1


class Component(object):
    def __init__(self, name, type_id, amount=1, group_id=-1):
        self.name = name
        self.type_id = type_id
        self.amount = amount
        self.group_id = group_id
        
        self.components = {}
        
    def __str__(self):
        return "Component (" + self.name + ", id=" + str(self.type_id) + ", group_id=" + str(self.group_id) + ": amount -> " + str(self.amount)


class Manufacturing(DataAccumulator):
    """
    Manufacturing requirements
    
    self.groups = {
        <group>: description,
        <group>: description,
        <group>: description,
        <group>: description,
    }
    """
    def __init__(self):
        super(Manufacturing, self).__init__()
        
        self._set_data_descriptor("manufacturing")
        self._set_data_url("http://www.eve-markets.net/detail.php?typeid=%s#industry")
        
        self.groups = Groups()
        self.groups.load_data()
        
    def _insert_entry_from_page_text(self, data_id, data_text):
        soup = BeautifulSoup(data_text)
        
        if 'Sorry' in [v.string for v in soup.find_all('h2')] or 'Error' in [v.string for v in soup.find_all('h1')]:
            # The item with this typeid does not exist!
            manufactured_component = Component("Empty", data_id)
            manufactured_component.components = {-1: Component("Empty", -1)}
            self.data[data_id] = manufactured_component
            return False
        
        type_name = soup.find_all('h1')[0].string
        
        group_id = -1
        
        # Let's try to decipher the group
        forms = soup.find_all('form')
        for form in forms:
            form_anchors = form.find_all('a')
            for anchor in form_anchors:
                if anchor.string == 'Browse Market Group':
                    group_url = anchor.get('href')
                    group_id = get_group_id_from_url(group_url)
                    self.groups.add_data(group_id)
        
        manufactured_component = Component(type_name, data_id, 1, group_id=group_id)
        
        for_unit_count = 1
        
        manufacturing_specified = False
        for div in soup.find_all('div'):
            for c in div.contents:
                if c.name == 'h4' and c.string == 'Manufacturing':
                    # This should happen only once if there is a manufacturing bit
                    
                    for sub_div in div.find_all('div'):
                        if sub_div.get('class')[0] == 'displaylist_footer_multi':
                            digits = 3
                            while for_unit_count == 1 and digits > 0:
                                try:
                                    for_unit_string = sub_div.find_all('span')[0].string[10:10 + digits]
                                    for_unit_count = int(for_unit_string)
                                except ValueError, e:
                                    pass
                                
                                digits -= 1
                    
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

        self.data[data_id] = manufactured_component
        
        return True

    def load_line(self, line):
        """ 
        data_id|group_name
        """
        parts = line.split('*')
        manufactured_component_str = parts[0].strip()
        manufactured_component_str_parts = manufactured_component_str.split('|') 
        manufactured_type_id = int(manufactured_component_str_parts[0])
        manufactured_type_name = manufactured_component_str_parts[1]
        manufactured_group_id = int(manufactured_component_str_parts[2])
        
        manufactured_component = Component(manufactured_type_name, manufactured_type_id, group_id=manufactured_group_id) 
        
        component_parts = parts[1].strip().split(' ')
        for component_str in component_parts:
            component_str_parts = component_str.split('|')
            
            component_type_id = int(component_str_parts[0])
            component_amount = float(component_str_parts[1])
            
            manufactured_component.components[component_type_id] = Component("", component_type_id, component_amount)
            
        self.data[manufactured_type_id] = manufactured_component
    
    def save_entry(self, f, data_id):
        component = self.data[data_id]
        f.write(str(component.type_id) + "|" + component.name + "|" + str(component.group_id))
        f.write(' * ')
        
        entries = component.components.keys()
        for type_id in entries:
            entry = component.components[type_id]
            f.write(str(entry.type_id) + "|" + str(entry.amount) + " ")
            f.write('\n')
            
    def finish(self):
        self.groups.save_data()
        
        self.save_data()

if __name__ == "__main__":
    m = Manufacturing()
    
    print "Loading existing manufacturing"
    m.load_data()
    print "Done!"
    
    excepted = True
    
    if excepted:
        try:
            m.build_data(start_id=0, end_id=40000)
                
        except Exception, e:
            print "A problem occurred!"
            print str(e)
        finally:
            m.finish()
    else:
        m.build_data(start_id=0, end_id=40000)
        
    
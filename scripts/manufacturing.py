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
from components import Component

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
        
    def _get_for_unit_count(self, div):
        for_unit_count = 1
        for sub_div in div.find_all('div'):
            if sub_div.get('class')[0] == 'displaylist_footer_multi':
                digits = 3
                while for_unit_count == 1 and digits > 0:
                    try:
                        for_unit_string = sub_div.find_all('span')[0].string[10:10 + digits]
                        for_unit_count = int(for_unit_string)
                    except ValueError, e:
                        print "Could not find number" 
                    
                    digits -= 1
                    
        return for_unit_count
        
    def _get_components(self, div, for_unit_count):
        components = {}
        
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
            
            components[component_type_id] = Component(component_name, component_type_id, component_amount)
        
        return components
        
    def _insert_entry_from_page_text(self, data_id, data_text):
        soup = BeautifulSoup(data_text)
        
        type_name = soup.find_all('h1')[0].string.encode('utf8')
        
        if 'Sorry' in [v.string for v in soup.find_all('h2')] or 'Error' in [v.string for v in soup.find_all('h1')]:
            # The item with this typeid does not exist!
            manufactured_component = Component(type_name, data_id)
            manufactured_component.components = {-1: Component("None", -1)}
            self.data[data_id] = manufactured_component
            return False
        
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
                    
        volume = 9999999999
        
        # Let's try to decipher the volume
        forms = soup.find_all('form')
        for form in forms:
            if form.get('name') == 'type_add':
                dds = form.find_all('dd')
                mm_string = str(dds[1])
                mm_string = mm_string.replace('<dd>', '')
                mm_string = mm_string[0:mm_string.index('<sup>') - 1]
                volume = float(mm_string)
#            form_anchors = form.find_all('a')
#            for anchor in form_anchors:
#                if anchor.string == 'Browse Market Group':
#                    group_url = anchor.get('href')
#                    group_id = get_group_id_from_url(group_url)
#                    self.groups.add_data(group_id)
        
        manufactured_component = Component(type_name, data_id, 1, group_id=group_id, volume=volume)
        
        for_unit_count = 1
        
        manufacturing_specified = False
        reprocessing_specified = False
        
        for div in soup.find_all('div'):
            for c in div.contents:
                if c.name == 'h4' and c.string == 'Manufacturing':
                    # This should happen only once if there is a manufacturing bit
                    manufacturing_specified = True
                    for_unit_count = self._get_for_unit_count(div)
                    manufactured_component.components = self._get_components(div, for_unit_count)
                        
                if c.name == 'h4' and c.string == 'Reprocessing':
                    # This should happen only once if there is a reprocessing bit
                    reprocessing_specified = True
                    for_unit_count = self._get_for_unit_count(div)
                    manufactured_component.reprocessing = self._get_components(div, for_unit_count)
        
        if not manufacturing_specified:
            manufactured_component.components = {-1: Component("Empty", -1)}
            
        if not reprocessing_specified:
            manufactured_component.reprocessing = {-1: Component("Empty", -1)}

        self.data[data_id] = manufactured_component
        
        return True
    
    def is_entry_valid(self, type_id):
        if self.data[type_id].name == "Empty":
            return False
        else:
            return True
        
    def get_full_requirements_dict(self, type_id):
        
        if type_id == -1:
            return None
        
        if not self.data.has_key(type_id):
            self.add_data(type_id)
            
        final_requirements = {}
        if type_id not in self.data:
            raise Exception("Requirement for " + str(type_id) + " not found!")
        
        manufactured_component = self.data[type_id]
        
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
        
    def get_full_reprocessing_dict(self, type_id):
        
        if type_id == -1:
            return None
        
        if not self.data.has_key(type_id):
            self.add_data(type_id)
            
        final_requirements = {}
        if type_id not in self.data:
            raise Exception("Requirement for " + str(type_id) + " not found!")
        
        reprocessed_component = self.data[type_id]
        
        for component_id in reprocessed_component.reprocessing.keys():
            # Check if we need to recurse:
            sub_requirements = {}
            component = reprocessed_component.reprocessing[component_id]
            
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
        
    def fetch_all_valid_ids(self):
        list_page_text = self.d.retry_fetch_data("http://www.eve-markets.net/lookup.php?search=")
        
        soup = BeautifulSoup(list_page_text)
        anchors = soup.find_all('a')
        
        all_ids = []
        
        for anchor in anchors:
            url = anchor.get('href')
            type_id = get_typeid_from_url(url)
            if type_id != -1:
                all_ids.append(type_id)
        
        all_ids.sort()        
        return all_ids

    def load_line(self, line):
        """ 
        data_id|group_name
        """
        try:
            parts = line.split(' -> ')
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
        except Exception, e:
            print "Load line failed on '" + line + "': " + str(e)
    
    def save_entry(self, f, data_id):
        component = self.data[data_id]
        f.write(str(component.type_id) + "|" + component.name + "|" + str(component.group_id))
        f.write(' -> ')
        
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
    
    ids = m.fetch_all_valid_ids()
    #ids = [36]
    
    excepted = True
    
    if excepted:
        try:
            m.build_data(ids_to_check=ids)
                
        except Exception, e:
            print "A problem occurred!"
            print str(e)
        finally:
            m.finish()
    else:
        m.build_data(ids_to_check=ids)
        
    
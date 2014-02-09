from downloader import Downloader
import os
from abc import ABCMeta, abstractmethod
import shutil
import requests


class DataAccumulator:
    __metaclass__ = ABCMeta
    
    def __init__(self):
        self.d = Downloader(wait=0.0)
        
        self._clear()
        
    def _clear(self):
        self.data = {}
        
    def _set_data_descriptor(self, data_descriptor):
        self.data_descriptor = data_descriptor
        self.requirements_filename = self.data_descriptor + ".txt"
        
    def _set_data_url(self, data_url):
        self.data_url = data_url

    def build_data(self, ids_to_check=None, start_id=None, end_id=None):
        force = False
        if not ids_to_check:
            if not end_id:
                end_id = start_id + 1
            ids_to_check = range(start_id, end_id)
        
        for id_to_check in ids_to_check:
            if id_to_check not in self.data or force:
                try:
                    if self.add_data(id_to_check):
                        print "Added: " + str(self.data[id_to_check])
                    else:
                        #print str(id_to_check) + " doesn't exist..."
                        pass
                except requests.exceptions.RequestException, e:
                    print "Request HTTP Error: " + str(e)
                
            else:
                print "Skipping type " + str(id_to_check) + "!"
                
            if id_to_check % 1000 == 0:
                self.save_data()


    @abstractmethod
    def is_entry_valid(self, type_id):
        pass

    def get_valid_data_ids(self):
        ids = []
        for component_id in self.data:
            if self.is_entry_valid(component_id):
                ids.append(component_id)
        return ids
    
    @abstractmethod
    def finish(self):
        pass
                
    def save_page(self, page_filename, market_data):
        
        if not os.path.exists(os.path.dirname(page_filename)):
            os.mkdir(os.path.dirname(page_filename))
            
        f = open(page_filename, 'w')
        f.write(market_data.encode('utf8'))
        f.close()

    @abstractmethod
    def load_line(self, line):
        pass

    def load_data(self, filename=None):
        if not filename:
            filename = self.requirements_filename
        
        self._clear()
        
        if os.path.exists(filename):
            f = open(filename, 'r')
            for line in f:
                try:
                    self.load_line(line)
                except Exception, e:
                    print str(e)
                    
            f.close()
            
    def _get_cache_filename(self, data_id):
        page_dir = self.data_descriptor + "_pages"
        subdir = os.path.join(page_dir, str(data_id / 1000))
        
        if not os.path.exists(subdir):
            os.makedirs(subdir)
        
        cache_filename = os.path.join(subdir, str(data_id) + ".htm")
        return cache_filename
            
    @abstractmethod
    def save_entry(self, entry_id):
        pass
    
    @abstractmethod
    def _insert_entry_from_page_text(self, data_id, group_data):
        pass

    def save_data(self, filename=None):
        if not filename:
            filename = self.requirements_filename
        
        if os.path.exists(filename):
            backup_filename = filename + ".bak"
            if os.path.exists(backup_filename):
                os.remove(backup_filename)
                
            shutil.copy(filename, backup_filename)
        
        f = open(filename, 'w')
        
        keys = self.data.keys()
        keys.sort()
        
        for data_id in keys:
            self.save_entry(f, data_id)
        f.close()
        
        print self.data_descriptor + " saved."
        
    def add_data(self, data_id):
        
        data_url = self.data_url % data_id
        cache_filename = self._get_cache_filename(data_id)
        
        page_text = None
        if not os.path.exists(cache_filename):
            page_text = self.d.retry_fetch_data(data_url)
            
        else:
            #print "Using cache: " + cache_filename
            f = open(cache_filename, 'r')
            page_text = f.read()
            page_text = page_text.decode('utf8')
            f.close()
            
            if len(page_text) == 0:
                os.remove(cache_filename)
                
                print "Bogus cache, retrying download..."
                page_text = self.d.retry_fetch_data(data_url)
        
        if not page_text:
            raise Exception("Failed download!")
            return False
        else:
            self.save_page(cache_filename, page_text)
        
        success = self._insert_entry_from_page_text(data_id, page_text)
        
        if page_text:
            del page_text
        
        return True
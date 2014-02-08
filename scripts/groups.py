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

def get_group_from_url(url):
    m = re.match(".*group=(\d+).*", url)
    if m:
        return int(m.groups()[0])
    return -1

class Groups(DataAccumulator):
    """
    Group descriptions
    
    self.groups = {
        <group>: description,
        <group>: description,
        <group>: description,
        <group>: description,
    }
    """
    def __init__(self):
        super(Groups, self).__init__()
        
        self._set_data_descriptor("groups")
        self._set_data_url("http://www.eve-markets.net/browse?group=%s")
        
    def _insert_entry_from_page_text(self, data_id, data_text):
        soup = BeautifulSoup(data_text)
        
        group_paragraph = soup.find_all('p')[1]
        
        group_anchors = group_paragraph.find_all('a')
        group_parts = [a.string for a in group_anchors]
        group_name = " > ".join(group_parts[1:])
        
        self.data[data_id] = group_name
        
        return True

    def load_line(self, line):
        """ 
        data_id|group_name
        """
        data_parts = line.split('|')
        data_id = int(data_parts[0])
        group_name = data_parts[1].strip()
        
        self.data[data_id] = group_name
    
    def save_entry(self, f, data_id):
        group_name = self.data[data_id]
        f.write(str(data_id) + "|" + group_name)
        f.write('\n')
        
    def finish(self):
        self.save_data()

if __name__ == "__main__":
    g = Groups()
    
    print "Loading existing groups"
    g.load_data()
    print "Done!"
    
    excepted=False
    
    if excepted:
        try:
            g.build_data(1000)
                
        except Exception, e:
            print "A problem occurred!"
            print str(e)
        finally:
            g.save_data()
    else:
        g.build_data(1000)
        
    
from downloader import Downloader
import os
from abc import ABCMeta, abstractmethod
import shutil
import requests
import json
import cPickle as pickle
from manufacturing import Manufacturing
from prices import Prices
from groups import Groups
        

class ProfitChecker:
    __metaclass__ = ABCMeta
    
    def __init__(self):
        self.d = Downloader(wait=0.0)
        self.m = Manufacturing()
        self.p = Prices()
        self.g = Groups()
        
        self.results = {}
        
    def start(self):
        self.all_valid_ids = self.m.fetch_all_valid_ids()
        
        self.m.load_data()
        self.p.load_data()
        self.g.load_data()
        self.p.warm_up(self.all_valid_ids)
    
    
    def check_manufacturing_cost(self, type_id):
        requirements = self.m.get_full_requirements_dict(type_id)
    
        requirement_ids = requirements.keys()
        prices = self.p.get_component_prices(requirement_ids)
        
        cost = 0
        for requirement_id in requirement_ids:
            cost += requirements[requirement_id] * prices[requirement_ids.index(requirement_id)]
    
        return cost

    def check_profit_bulk(self, type_ids=None):
        if not type_ids:
            type_ids = self.all_valid_ids
            
        f = open('type_ids.txt', 'w')
        for type_id in type_ids:
            f.write(str(type_id) + "\n")
        f.close()
        
        final_ids = self.filter_type_ids(type_ids)
            
        for type_id in type_ids:
            self.check_profit(type_id)

    @abstractmethod
    def filter_type_ids(self, type_ids):
        pass

    @abstractmethod
    def check_profit(self, type_id):
        pass
        
    @abstractmethod
    def write_output(self, filename):
        pass

    def finish(self, filename):
        self.write_output(filename)
        
        self.m.finish()
        self.g.finish()

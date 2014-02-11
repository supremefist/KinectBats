from downloader import Downloader
import os
from abc import ABCMeta, abstractmethod
import shutil
import requests
import json
import cPickle as pickle
from manufacturing import Manufacturing
from prices import Prices, PriceType
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
        prices = self.p.get_component_prices(requirement_ids, price_type=PriceType.SELL_PERCENTILE)
        
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
            
        for type_id in final_ids:
            self.check_profit(type_id)

    @abstractmethod
    def filter_type_ids(self, type_ids):
        pass

    @abstractmethod
    def check_profit(self, type_id):
        pass
    
    def add_basics_to_result(self, result, type_id):
        component = self.m.data[type_id]
        
        group_name = "Unknown"
        if component.group_id in self.g.data:
            group_name = self.g.data[component.group_id]
            
        result['name'] = component.name
        result['group'] = group_name
        result['volume'] = component.volume
            
        return result
    
    def write_output(self, filename):
        type_ids = self.results.keys()
        
        if len(type_ids) > 0:
            f = open(filename, 'w')
            
            
            
            if type(self.results[type_ids[0]]) == type([]):
                # We are writing a list of results within each type_id
                column_names = self.results[type_ids[0]][0].keys()
                column_names.sort()
                
                for key in column_names:
                    f.write(key + ",")
                f.write('\n')
                
                type_ids = self.results.keys()
                type_ids.sort()
                
                for type_id in type_ids:
                    for entry in self.results[type_id]:
                        for key in column_names:
                            f.write(str(entry[key]) + ",")
                        f.write('\n')
            else:
                # We have a single result for each type_id
                column_names = self.results[type_ids[0]].keys()
                column_names.sort()
                
                for key in column_names:
                    f.write(key + ",")
                f.write('\n')
                
                type_ids = self.results.keys()
                type_ids.sort()
                
                for type_id in type_ids:
                    for key in column_names:
                        f.write(str(self.results[type_id][key]) + ",")
                    f.write('\n')
        
            f.close()
        
        print "Calculated profitability for " + str(len(type_ids)) + " items!"

    @abstractmethod
    def filter_results(self):
        pass

    def finish(self, filename):
        self.write_output(filename)
        self.p.finish()
        self.m.finish()
        self.g.finish()

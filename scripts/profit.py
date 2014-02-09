from manufacturing import Manufacturing
from prices import Prices
from groups import Groups

class ManufacturingChecker(object):
    def __init__(self):
        self.m = Manufacturing()
        self.p = Prices()
        self.g = Groups()
        
        self.results = {}
    
    def start(self):
        self.m.load_data()
        self.p.load_data()
        self.g.load_data()
        self.p.warm_up(self.m.fetch_all_valid_ids())
        
    
    def check_manufacturing_cost(self, type_id):
        requirements = self.m.get_full_requirements_dict(type_id)
    
        requirement_ids = requirements.keys()
        prices = self.p.get_component_prices(requirement_ids)
        
        cost = 0
        for requirement_id in requirement_ids:
            cost += requirements[requirement_id] * prices[requirement_ids.index(requirement_id)]
    
        return cost
    
    def check_market_price(self, type_id):
        price = self.p.get_component_prices([type_id])[0]
        
        return price
    
    def check_manufacturing_profit_bulk(self, type_ids=None):
        if not type_ids:
            type_ids = self.m.fetch_all_valid_ids()
            
        for type_id in type_ids:
            component = self.m.data[type_id]
            if component.name == 'Empty':
                continue
            group = self.g.data[component.group_id]
            
            valid = True
            
            if 'faction' in group.lower():
                valid = False
                
            if 'blueprint' in group.lower():
                valid = False
                
            if 'II' in component.name:
                valid = False
                
            if component.name.lower() == 'drake' or type_id == 24698:
                print "Drake: " + str(valid)
                exit(-1)
            
            if valid:
                self.check_manufacturing_profit(type_id)
                if self.results.has_key(type_id):
                    print self.results[type_id]
    
    def check_manufacturing_profit(self, type_id):
        cost = self.check_manufacturing_cost(type_id)
        if cost == 0:
            cost = 999999999999
        
        price = -1
        if type_id in self.m.data and self.m.data[type_id].name != 'Empty':
            price = self.check_market_price(type_id)
        profitability = price / cost
        
        component = self.m.data[type_id]
        
        if profitability != -1:
            self.results[type_id] = {"name": self.m.data[type_id].name, 
                                     'price': price, 
                                     'cost': cost, 
                                     'profitability': round(profitability, 4),
                                     'group': self.g.data[component.group_id] 
                                     }
            
        if type_id % 100 == 0:
            self.finish()
        
        return profitability
    
    def finish(self):
        f = open('results.csv', 'w')
        f.write("Name,Price,Cost,Profitability,Group\n")
        
        type_ids = self.results.keys()
        type_ids.sort()
        
        for type_id in type_ids:
            result = self.results[type_id]
            f.write(result['name'] + "," + str(result['price']) + "," + str(result['cost']) + "," + str(result['profitability']) + "," + str(result['group'] + "\n"))
        
        f.close()
        
        self.m.finish()
        self.p.finish()
        self.g.finish()

if __name__ == "__main__":

    drake = 24698
    orca = 28606
    
    test_id = 2869
    
    excepted = False
    if excepted:
        c = None 
        try:
            c = ManufacturingChecker()
            c.start()
            
            c.check_manufacturing_profit_bulk()
        except Exception, e:
            print str(e)
            
        finally:
            c.finish()
    else:
        c = ManufacturingChecker()
        c.start()
        c.check_manufacturing_profit_bulk()
        c.finish()
        


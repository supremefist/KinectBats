from manufacturing_requirements import ManufacturingRequirements
from prices import Prices

class ManufacturingChecker(object):
    def __init__(self):
        self.m = ManufacturingRequirements()
        self.m.load_requirements()
        self.p = Prices()
        
        self.results = {}
    
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
    
    def check_manufacturing_profit_bulk(self, type_ids):
        for type_id in type_ids:
            self.check_manufacturing_profit(type_id)
            if self.results.has_key(type_id):
                print self.results[type_id]
    
    def check_manufacturing_profit(self, type_id):
        cost = self.check_manufacturing_cost(type_id)
        if cost == 0:
            cost = 999999999999
        
        price = -1
        if type_id in self.m.requirements and self.m.requirements[type_id].name != 'Empty':
            price = self.check_market_price(type_id)
        profitability = price / cost
        
        if profitability != -1:
            self.results[type_id] = {"name": self.m.requirements[type_id].name, 
                                     'price': price, 
                                     'cost': cost, 
                                     'profitability': round(profitability, 4), 
                                     }
        
        return profitability
    
    def finish(self):
        f = open('results.csv', 'w')
        f.write("Name,Price,Cost,Profitability\n")
        
        type_ids = self.results.keys()
        type_ids.sort()
        
        for type_id in type_ids:
            result = self.results[type_id]
            f.write(result['name'] + "," + str(result['price']) + "," + str(result['cost']) + "," + str(result['profitability']) + "\n")
        
        f.close()
        
        self.m.finish()

if __name__ == "__main__":

    drake = 24698
    orca = 28606
    
    typeids = [i for i in range(24000, 25000)]
    #typeids = [21013]
    
    excepted = False
    if excepted:
        try:
            c = ManufacturingChecker()
            
            c.check_manufacturing_profit_bulk(typeids)
        except Exception, e:
            print str(e)
            
        finally:
            c.finish()
    else:
            c = ManufacturingChecker()
            c.check_manufacturing_profit_bulk(typeids)
            c.finish()
        


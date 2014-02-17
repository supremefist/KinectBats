from manufacturing import Manufacturing
from prices import Prices, PriceType
from groups import Groups
from profit_checker import ProfitChecker

class ReprocessingChecker(ProfitChecker):
    def __init__(self):
        super(ReprocessingChecker, self).__init__()
    
    def check_market_price(self, type_id):
        price = self.p.get_component_prices([type_id], price_type=PriceType.SELL_PERCENTILE)[0]
        
        return price
    
    def filter_type_ids(self, type_ids):
        final_ids = []
        for type_id in type_ids:
            component = self.m.get_entry(type_id)
            group = "unknown"

            if component.group_id != -1:            
                group = self.g.get_entry(component.group_id)
                if not group:
                    group = "unknown"
            
            valid = True
            
            invalid_name_strings = []
            #invalid_name_strings = ['booster', 'sisters', 'domination', 'shadow', 'dread', 'alliance', ' ii', '\'', 'navy', 'fleet', 'blood', 'guristas', 'sansha', 'angel']
            invalid_group_strings = []
            #invalid_group_strings = ['advanced', 'faction', 'implants', 'unknown', 'infantry', 'trade goods', 'skills', 'blueprint', 'special edition', 'subsystems']
            
            lower_name = component.name.lower()
            for invalid_name_string in invalid_name_strings:
                if invalid_name_string in lower_name:
                    valid = False
            
            lower_group = group.lower()
            for invalid_group_string in invalid_group_strings:
                if invalid_group_string in lower_group:
                    valid = False
                    
            if valid:
                final_ids.append(type_id)
        return final_ids
    
    def check_profit(self, type_id):
        value = self.check_reprocessing_value(type_id)
        
        price = -1
        if type_id in self.m.data and self.m.data[type_id].name != 'Empty':
            price = self.check_market_price(type_id)
        
        if price == 0:
            price = -1
        
        profitability = value / price 
        
        if profitability != -1 and value > -1:
            result = {}
            self.add_basics_to_result(result, type_id)
            
            result['price'] = price
            result['value'] = value
            result['profitability'] = profitability
            
            self.results[type_id] = result
            
        return profitability
    
    def filter_results(self):
        pass
    

if __name__ == "__main__":

    drake = 24698
    orca = 28606
    
    test_id = 2869
    
    excepted = False
    if excepted:
        c = None 
        try:
            c = ReprocessingChecker()
            c.start()
            
            c.check_profit_bulk()
        except Exception, e:
            print str(e)
            
        finally:
            c.finish('reprocessing_profit.csv')
    else:
        c = ReprocessingChecker()
        c.start()
        c.check_profit_bulk()
        c.finish('reprocessing_profit.csv')
        


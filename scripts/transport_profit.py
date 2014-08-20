from manufacturing import Manufacturing
from prices import Prices, Region, PriceType
from groups import Groups
from profit_checker import ProfitChecker

class TransportChecker(ProfitChecker):
    def __init__(self):
        super(TransportChecker, self).__init__()
        
    def check_profit(self, type_id):
        component = self.m.get_entry(type_id)
        print "Calculating profits for " + str(component.name) + " ..."
        
        regions = Region.get_all_regions()
        
        for i in range(0, len(regions)):
            source_region = regions[i]
            
            for j in range((i + 1), len(regions)):
                dest_region = regions[j]
                
                buy_type_volume = PriceType.SELL_VOLUME
                sell_type_volume = PriceType.SELL_VOLUME
                
                buy_type = PriceType.SELL_MIN
                sell_type = PriceType.SELL_MIN
                
                source_sell_volume = self.p.get_component_prices([type_id], sell_type_volume, source_region)[0]
                source_buy_volume = self.p.get_component_prices([type_id], buy_type_volume, source_region)[0]
                dest_sell_volume = self.p.get_component_prices([type_id], sell_type_volume, dest_region)[0]
                dest_buy_volume = self.p.get_component_prices([type_id], buy_type_volume, dest_region)[0]
                
                source_sell_price = self.p.get_component_prices([type_id], sell_type, source_region)[0]
                source_buy_price = self.p.get_component_prices([type_id], buy_type, source_region)[0]
                
                dest_sell_price = self.p.get_component_prices([type_id], sell_type, dest_region)[0]
                dest_buy_price = self.p.get_component_prices([type_id], buy_type, dest_region)[0]
                
                forward_profit = -9999999999999999
                backward_profit = -9999999999999999
                if dest_buy_volume > 0 and source_sell_volume > 0:
                    forward_profit = dest_buy_price - source_sell_price
                    
                if dest_sell_volume > 0 and source_buy_volume > 0:
                    backward_profit = source_buy_price - dest_sell_price
                
                final_source = dest_region
                final_destination = source_region
                final_source_price = dest_sell_price
                final_dest_price = source_buy_price
                final_profit = backward_profit
                
                if forward_profit > backward_profit:
                    final_source = source_region
                    final_destination = dest_region
                    final_profit = forward_profit
                    final_source_price = source_sell_price
                    final_dest_price = dest_buy_price
                
                    
                    
                profit_m3 = final_profit
                if component.volume > 0:
                    profit_m3 = float(final_profit) / float(component.volume)
                    
                profit_ratio = 0
                if final_source_price > 0:
                    profit_ratio = final_dest_price / final_source_price
                
                
                if final_profit > 0:
                    if type_id not in self.results:
                        self.results[type_id] = []
                
                    
                    result = {}
                    self.add_basics_to_result(result, type_id)
                    result['source'] = Region.get_region_string(final_source)
                    result['destination'] = Region.get_region_string(final_destination)
                    result['buy_price'] = final_source_price
                    result['sell_price'] = final_dest_price
                    result['profit'] = final_profit
                    result['profit/m3'] = profit_m3
                    result['profit_ratio'] = profit_ratio
                
                    self.results[type_id].append(result)
    
    def filter_results(self):
        for type_id in self.results.keys():
            for result in self.results[type_id]:
                remove = False
                if result['buy_price'] > 1000000000:
                    remove = True
                    
                if remove:
                    self.results[type_id].remove(result)
                
            
    
    def filter_type_ids(self, type_ids):
        final_type_ids = []
        for type_id in type_ids:
            component = self.m.get_entry(type_id)
            
            if component.volume < 1.0:
                final_type_ids.append(type_id)
        
        return final_type_ids
    
if __name__ == "__main__":

    drake = 24698
    orca = 28606
    
    test_id = 2869
    
    type_ids = None
    
    excepted = True
    if excepted:
        c = None 
        try:
            c = TransportChecker()
            c.start()
            
            c.check_profit_bulk(type_ids=type_ids)
        except Exception, e:
            print str(e)
            
        finally:
            c.finish('transport_profit.csv')
    else:
        c = TransportChecker()
        c.start()
        c.check_profit_bulk(type_ids=type_ids)
        c.finish('transport_profit.csv')
        


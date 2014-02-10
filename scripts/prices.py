from bs4 import BeautifulSoup
import requests
from lxml import etree
from downloader import Downloader
from data_accumulator import DataAccumulator
from manufacturing import Manufacturing

class Region:
    """
    http://eve-marketdata.com/developers/regions.php
    """
    # Jita, Forge
    JITA =  10000002
    
    # Hek, Metropolis
    HEK =   10000042
    
    # Amarr, Domain
    AMARR = 10000043
    
    # Dodixie, Sinq Laison
    DODIXIE = 10000032
    
    # Rens, Heimatar
    RENS = 10000030
    
    @classmethod
    def get_region_string(cls, region_id):
        if region_id == Region.JITA:
            return "Forge"
        elif region_id == Region.HEK:
            return "Metropolis"
        elif region_id == Region.AMARR:
            return "Domain"
        elif region_id == Region.DODIXIE:
            return "Sinq Laison"
        elif region_id == Region.RENS:
            return "Heimatar"
        else:
            return "Unknown"
        
        return [Region.JITA, Region.AMARR, Region.DODIXIE, Region.HEK, Region.RENS]
    
    @classmethod
    def get_all_regions(cls):
        return [Region.JITA, Region.AMARR, Region.DODIXIE, Region.HEK, Region.RENS]

class PriceType:
    BUY_VOLUME = './/type/buy/volume'
    BUY_MAX = './/type/buy/max'
    BUY_MIN = './/type/buy/min'
    BUY_STDDEV = './/type/buy/stddev'
    BUY_MEDIAN = './/type/buy/median'
    BUY_PERCENTILE = './/type/buy/percentile'
    
    SELL_VOLUME = './/type/sell/volume'
    SELL_MAX = './/type/sell/max'
    SELL_MIN = './/type/sell/min'
    SELL_STDDEV = './/type/sell/stddev'
    SELL_MEDIAN = './/type/sell/median'
    SELL_PERCENTILE = './/type/sell/percentile'

class Prices(DataAccumulator):
    """
    Prices
    
    self.data = {
        <type_id>: {
            <price_type>: {
                <region_id>: <price_value>,
                <region_id>: <price_value>,
                <region_id>: <price_value>
            }
        },
    }
    """
    def __init__(self):
        super(Prices, self).__init__()
        
        self._set_data_descriptor("prices")
        self._set_data_url("http://api.eve-central.com/api/marketstat?typeid=%s&regionlimit=10000002")
        
    def _insert_entry_from_page_text(self, data_id, data_text):
#        mineral_etree = etree.fromstring(str(data_text))   
#        type_values = [float(str(b.text).strip()) for b in mineral_etree.iterfind('.//type/buy/median')]
#        
#        self.data[data_id] = float(type_values[0])
#        
#        return True
        raise NotImplementedError()

    def load_line(self, line):
        """ 
        data_id -> type, region, price | type, region, price | type, region, price  
        """
        data_parts = line.split('|')
        data_id = int(data_parts[0])
        price = float(data_parts[1].strip())
        
        self.data[data_id] = price
        
    def get_component_prices(self, data_ids, price_type=PriceType.BUY_MEDIAN, region_id=Region.JITA):
        """
        self.data = {
            <type_id>: {
                <price_type>: {
                    <region_id>: <price_value>,
                    <region_id>: <price_value>,
                    <region_id>: <price_value>
                }
            },
        }
        """
        self.add_bulk_data(data_ids)
        
        prices = []
        for data_id in data_ids:
            prices.append(self.data[data_id][price_type][region_id])
            
        return prices
    
    def save_entry(self, f, data_id):
        """
        data_id -> type, region, price | type, region, price | type, region, price
        """  
        
        price = self.data[data_id]
        f.write(str(data_id) + "|" + str(price))
        f.write('\n')
        
    def finish(self):
        self.save_data()
        
    def warm_up(self, type_ids):
        query_size = 100
        end_id = 0
        start_id = 0
        for i in range(0, len(type_ids)/query_size):
            start_id = i * query_size
            end_id = (i + 1) * query_size
            
            self.add_bulk_data(type_ids[start_id: end_id])   
            
        start_id = end_id
        end_id = len(type_ids)
        
        self.add_bulk_data(type_ids[start_id: end_id])
        
    def add_bulk_data(self, data_ids):
        """
        self.data = {
            <type_id>: {
                <price_type>: {
                    <region_id>: <price_value>,
                    <region_id>: <price_value>,
                    <region_id>: <price_value>
                }
            },
        }
        """
        url = "http://api.eve-central.com/api/marketstat?%sregionlimit=%s"
        
        need_fetch = False
        for data_id in data_ids:
            if data_id not in self.data:
                need_fetch = True
        
        if need_fetch:
            types_string = ""
            for data_id in data_ids:
                types_string += "typeid=" + str(data_id) + "&"
            
            regions = Region.get_all_regions()
            for region_id in regions:
                final_url = url % (types_string, region_id)
                data_text = self.d.retry_fetch_data(final_url)
                mineral_etree = etree.fromstring(str(data_text))
                
                price_types = [PriceType.BUY_VOLUME, 
                               PriceType.BUY_MAX,
                               PriceType.BUY_MIN,
                               PriceType.BUY_STDDEV,
                               PriceType.BUY_MEDIAN,
                               PriceType.BUY_PERCENTILE,
                               
                               PriceType.SELL_VOLUME,
                               PriceType.SELL_MAX,
                               PriceType.SELL_MIN,
                               PriceType.SELL_STDDEV,
                               PriceType.SELL_MEDIAN,
                               PriceType.SELL_PERCENTILE
                               ]
                
                for price_type in price_types:            
                    prices = [float(str(b.text).strip()) for b in mineral_etree.iterfind(price_type)]
                    for idx, price in enumerate(prices):
                        type_id = data_ids[idx]
                        
                        if type_id not in self.data:
                            self.data[type_id] = {}
                        
                        if price_type not in self.data[type_id]:
                            self.data[type_id][price_type] = {}
                            
                        self.data[type_id][price_type][region_id] = price 
    
    def is_entry_valid(self, type_id):
        return True
    
if __name__ == "__main__":
    d = Prices()
    d.load_data()
    print "Done!"
    
    m = Manufacturing()
    m.load_data()
    
    valid_ids = m.get_valid_data_ids()
    
    excepted = True
    
    if excepted:
        try:
            d.warm_up(valid_ids)
                
        except Exception, e:
            print "A problem occurred!"
            print str(e)
        finally:
            d.save_data()
    else:
        d.warm_up(valid_ids)
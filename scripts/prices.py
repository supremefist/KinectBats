from bs4 import BeautifulSoup
import requests
from lxml import etree
from downloader import Downloader
from data_accumulator import DataAccumulator
from manufacturing import Manufacturing


class Prices(DataAccumulator):
    
    """
    Prices
    
    self.data = {
        <type_id>: price,
        <type_id>: price,
        <type_id>: price,
        <grouptype_id>: price,
    }
    """
    def __init__(self):
        super(Prices, self).__init__()
        
        self._set_data_descriptor("prices")
        self._set_data_url("http://api.eve-central.com/api/marketstat?typeid=%s&regionlimit=10000002")
        
    def _insert_entry_from_page_text(self, data_id, data_text):
        mineral_etree = etree.fromstring(str(data_text))   
        type_values = [float(str(b.text).strip()) for b in mineral_etree.iterfind('.//type/buy/median')]
        
        self.data[data_id] = float(type_values[0])
        
        return True

    def load_line(self, line):
        """ 
        data_id|price
        """
        data_parts = line.split('|')
        data_id = int(data_parts[0])
        price = float(data_parts[1].strip())
        
        self.data[data_id] = price
        
    def get_component_prices(self, data_ids):
        prices = []
        for data_id in data_ids:
            prices.append(self.data[data_id])
            
        return prices
    
    def save_entry(self, f, data_id):
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
        url = "http://api.eve-central.com/api/marketstat?%sregionlimit=10000002"
        
        need_fetch = False
        for data_id in data_ids:
            if data_id not in self.data:
                need_fetch = True
        
        if need_fetch:
            types_string = ""
            for data_id in data_ids:
                types_string += "typeid=" + str(data_id) + "&"
                
            data_text = self.d.retry_fetch_data(url % (types_string))
            mineral_etree = etree.fromstring(str(data_text))   
            prices = [float(str(b.text).strip()) for b in mineral_etree.iterfind('.//type/buy/median')]
            
            for idx, price in enumerate(prices):
                self.data[data_ids[idx]] = price
    
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
            d.build_data(ids_to_check=valid_ids)
                
        except Exception, e:
            print "A problem occurred!"
            print str(e)
        finally:
            d.save_data()
    else:
        d.build_data(1000)
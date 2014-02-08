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
        
        self.d.wait = 0
        
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
    
    def save_entry(self, f, data_id):
        price = self.data[data_id]
        f.write(str(data_id) + "|" + str(price))
        f.write('\n')
        
    def finish(self):
        self.save_data()
    
    def is_entry_valid(self, type_id):
        return True
    
        
class OldPrices(object):
    def __init__(self):
        self.d = Downloader(wait=0)
        self.prices = {}
    
    def download_component_prices(self, type_ids):    
        type_ids_str = ""
        for type_id in type_ids:
            type_ids_str += "typeid=%s&" % (type_id)
        
        prices_url = "" % type_ids_str
        
        prices_data = self.d.retry_fetch_data(prices_url)
    
        mineral_etree = etree.fromstring(str(prices_data))   
        type_values = [float(str(b.text).strip()) for b in mineral_etree.iterfind('.//type/buy/median')]
        
        prices = []
        for value in type_values:
            prices.append(value)
        
        return prices
    
    def warm_up(self, type_ids):
        query_size = 150
        end_id = 0
        start_id = 0
        for i in range(0, len(type_ids)/query_size):
            start_id = i * query_size
            end_id = (i + 1) * query_size
            
            self.get_component_prices(type_ids[start_id: end_id])   
            
        start_id = end_id
        end_id = len(type_ids)
        
        self.get_component_prices(type_ids[start_id: end_id])
        
    
    def get_component_prices(self, type_ids):
        need_fetch = False
        
        for type_id in type_ids:
            if type_id not in self.prices:
                need_fetch = True
            
        prices = []    
        if need_fetch:
            prices = self.download_component_prices(type_ids)
            for idx, price in enumerate(prices):
                self.prices[type_ids[idx]] = price
        else:
            for type_id in type_ids:
                prices.append(self.prices[type_id])
    
        return prices

def get_selling_price(fake=False):
    central_url = "http://api.eve-central.com/api/marketstat?typeid=%s&regionlimit=10000002" % type_id
    central_data = None

    if fake:
        central_url = "data//Raven.xml"
        f = open(central_url, 'r')
        central_data = f.read()
        f.close()
    else:
        print "Downloading " + central_url
        r  = requests.get(central_url)
        central_data = r.text
        print "Done"
        
    price_etree = etree.fromstring(central_data)   
    price_values = [float(str(b.text).strip()) for b in price_etree.iterfind('.//buy/median')]
    return float(price_values[0])




def get_mineral_prices(fake=False):
    minerals_url = "http://api.eve-central.com/api/marketstat?typeid=34&typeid=35&typeid=36&typeid=37&typeid=38&typeid=39&typeid=40&regionlimit=10000002"
    mineral_data = None
    
    if fake:
        minerals_url = "data//minerals.xml"
        f = open(minerals_url, 'r')
        mineral_data = f.read()
        f.close()
    else:
        print "Downloading " + minerals_url
        r  = requests.get(minerals_url)
        mineral_data = r.text
        print "Done"

    mineral_etree = etree.fromstring(mineral_data)   
    type_values = [float(str(b.text).strip()) for b in mineral_etree.iterfind('.//type/buy/median')]
    
    prices = {}
    prices['Tritanium'] = type_values[0]
    prices['Pyerite'] = type_values[1]
    prices['Mexallon'] = type_values[2]
    prices['Isogen'] = type_values[3]
    prices['Nocxium'] = type_values[4]
    prices['Zydrine'] = type_values[5]
    prices['Megacyte'] = type_values[6]
    
    return prices

def calculate_manufacturing_cost(manufacturing_requirements, component_prices):
    cost = 0
    for requirement in manufacturing_requirements:
        if requirement not in component_prices:
            raise Exception("Could not find " + requirement + " price!")
        
        cost += manufacturing_requirements[requirement]['amount'] * component_prices[requirement]
        
    return cost
        
if __name__ == "__main__":
    d = Prices()
    
    print "Loading existing groups"
    d.load_data()
    print "Done!"
    
    m = Manufacturing()
    m.load_data()
    
    valid_ids = m.get_valid_data_ids()
    print valid_ids
    
    excepted=True
    
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
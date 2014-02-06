from bs4 import BeautifulSoup
import requests
from lxml import etree

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


def get_component_prices(fake=False):
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

def get_manufacturing_requirements(fake=False):
    markets_url = "http://www.eve-markets.net/detail.php?typeid=%s#industry" % type_id
    market_data = None

    if fake:
        markets_url = "data//Raven.htm"
        f = open(markets_url, 'r')
        market_data = f.read()
        f.close()
    else:
        print "Downloading " + markets_url
        r  = requests.get(markets_url)
        market_data = r.text
        print "Done"
        
    market_soup = BeautifulSoup(market_data)
    manufacturing_requirements = {}

    markets_url = "http://www.eve-markets.net/detail.php?typeid=%s#industry" % type_id
    
    for div in market_soup.find_all('div'):
        for c in div.contents:
            if c.name == 'h4' and c.string == 'Manufacturing':
                dl = div.find_all('dl')[0]
                for dt in dl.find_all('dt'):
                    spans = dt.find_all('span')
                    name_span = spans[0]
                    amount_span = spans[1]
                    
                    component_name = name_span.find_all('a')[0].string
                    component_url = name_span.find_all('a')[0].get('href') + "#industry"
                    amount = int(amount_span.string)
                    
                    manufacturing_requirements[component_name] = {}
                    manufacturing_requirements[component_name]['amount'] = amount
                    manufacturing_requirements[component_name]['url'] = component_url
    
    return manufacturing_requirements

def calculate_manufacturing_cost(manufacturing_requirements, component_prices):
    cost = 0
    for requirement in manufacturing_requirements:
        if requirement not in component_prices:
            raise Exception("Could not find " + requirement + " price!")
        
        cost += manufacturing_requirements[requirement]['amount'] * component_prices[requirement]
        
    return cost
        
    
    
# Raven
type_id = 638

# Orca
#type_id = 28606

fake = False
    
component_prices = get_component_prices(fake)
manufacturing_requirements = get_manufacturing_requirements(fake)
selling_price = get_selling_price(fake)

cost = calculate_manufacturing_cost(manufacturing_requirements, component_prices)
print selling_price / cost
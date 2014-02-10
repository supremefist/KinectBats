from manufacturing import Manufacturing
from prices import Prices
from groups import Groups
from profit_checker import ProfitChecker

class TransportChecker(ProfitChecker):
    def __init__(self):
        super(TransportChecker, self).__init__()
        
    def check_profit_bulk(self, type_ids=None):
        pass
    
    def check_profit(self, type_id):
        pass
        
    def write_output(self, filename):
        pass
    
    def filter_type_ids(self, type_ids):
        return type_ids

if __name__ == "__main__":

    drake = 24698
    orca = 28606
    
    test_id = 2869
    
    excepted = False
    if excepted:
        c = None 
        try:
            c = TransportChecker()
            c.start()
            
            c.check_profit_bulk()
        except Exception, e:
            print str(e)
            
        finally:
            c.finish('transport_profit.csv')
    else:
        c = TransportChecker()
        c.start()
        c.check_profit_bulk()
        c.finish('transport_profit.csv')
        


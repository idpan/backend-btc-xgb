from data_scrapper.ohlcv_scrapper import get_btc_dataset
from helper.db_manager import DatabaseManager

try :
    df = get_btc_dataset()

    #=========testting=======
    df = df.tail(1)
    #=========testting=======


    db_manager = DatabaseManager()
    db_manager.write_ohlcv_to_db(df,'ohlcv_dataset')
except Exception as e : 
    print(f"❌ retrieved btc dataset failed: {e}")
else : 
    ohlcv_df = db_manager.read_table_to_df('ohlcv_dataset')
    print(ohlcv_df)
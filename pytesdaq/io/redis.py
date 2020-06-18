"""
TBD
"""
import numpy as np
import pytesdaq.config.settings as config
import walrus as wsredis
import struct


class RedisCore(object):
    """
    TBD
    """

    def __init__(self):
        """
        Args:
        """
        self.cnx = None
        self.host = None
        self.port = None
        self.password = None
 


    def connect(self, use_config=True, 
                host=str(), port=0, password=str()):
        """
        TDB
        """

        if use_config:
            self._extract_redis_info()

        if self.cnx is None:
            self.cnx = wsredis.Database(host=self.host,
                                        port=self.port,
                                        db=0)
        
   
            
    
    def add_hash(self,hash_name, key=str(), val=str(), key_val_dict=dict()):
        """
        TDB
        """
        if self.cnx is None:
            self.connect()

        table_dict = dict()
        if key and val:
            table_dict = {key: val}

        if key_val_dict:
            table_dict.update(key_val_dict)

        try:
            
            hash_table =  self.cnx.Hash(hash_name)
            hash_table.update(table_dict)
        except:
            pass


    def get_hash_val(self,hash_name,key):
        """
        TBD
        """

        if self.cnx is None:
            self.connect()
            
        val = []
        try:
            key_dict = self.get_hash_dict(hash_name,keys=key)
            if len(key_dict)==1:
                val = key_dict[key]
        except:
            pass

        return val
            

    


    def get_hash_dict(self,hash_name,keys=list()):
        """
        TBD
        """

        if self.cnx is None:
            self.connect()
        
        if isinstance(keys, str):
            keys = [keys]

        output_dict = dict()
        try:
            hash_table =  self.cnx.Hash(hash_name)
            if keys:
                for key in keys:
                    vals = hash_table.search(key)
                    for val in vals:
                        print(val)
                        output_dict[key] = val[1].decode()
                else:
                    output_dict = hash_table.as_dict(decode=True)
        except:
            pass

        return output_dict
        



    def add_stream(self,stream_name, data, metadata=dict()):
        """
        TBD
        """
        if self.cnx is None:
            self.connect()
        

        # encode data
        encoded_data = data.tobytes()
        fields = {'data': encoded_data}
        
        # metadata
        h,w = data.shape
        fields.update({"num_channels": h,
                       "num_samples": w})
        if metadata and isinstance(metadata,dict):
            fields.update(metadata)
        try:
            stream = db.Stream(stream_name)
            stream.add(fields,maxlen=200)
        except:
            pass


            
    def get_stream(self,stream_name):
        """
        TBD
        """
        if self.cnx is None:
            self.connect()
        
        data_array = []
        metadata = dict()
        try:
            stream = db.Stream(stream_name)
            data_stream = stream.read(count=1,block=2000,last_id='$')[0][1]
            
            # nd array
            #data_stream = data_stream[0][1]
            h = int(data_stream[b'num_channels'])
            w = int(data_stream[b'num_samples'])
            data_encoded = data_stream[b'data']
            data_array = np.frombuffer(data_encoded,dtype=np.int16).reshape(h,w)
            
            # metadata


        except:
            pass

        return (data_array,metadata)
    



    def _extract_redis_info(self):

        info = config.get_redis_info()
        self.host = info["host"]
        self.port = info["port"]
        self.password = info["password"]
      
    

        

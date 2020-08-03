from __future__ import print_function
import mysql.connector
from mysql.connector import errorcode
import time


class MySQLCore:
    
    def __init__(self, dbname = 'tesdaq'):

        self._dbname = dbname
        self._cnx = None
        self._host = None
        self._port = None
        self._password = None
        self._user = None
        


    def connect_manual(self,host,port,user,password):

        self._host = host
        self._port = port
        self._password = password
        self._user = user


        if self._cnx is None:
            try:
                self._cnx = mysql.connector.connect(user=self._user, password=self._password, 
                                                    host=self._host, port=self._port, 
                                                    database=self._dbname)
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                    print('Something is wrong with your user name or password')
                elif err.errno == errorcode.ER_BAD_DB_ERROR:
                    print('Database does not exist')
                else:
                    print(err)
            else:
                print('Database successfully connected!')
        return True    
                    
    
    def disconnect(self):
        if self._cnx is None:
            print('Not connected to any database!')
            return False
        self._cnx.close()
        self._cnx = None
        
    

    """
    def create_fridge_database(self):
        
        # sanity check
        if self._cnx is None:
            print('Not connected to any database!')
            return False
        
        # create command
        TABLES = {}
        create_stmt = 'CREATE TABLE test_db (Id INT PRIMARY KEY AUTO_INCREMENT, fridgeTime DATETIME, 
        daqTime BIGINT NOT NULL DEFAULT 0'
        for i in range(1, 16):
            create_stmt += ', lakeshore372_res{} FLOAT NOT NULL DEFAULT 0, lakeshore372_temp{} FLOAT NOT 
            NULL DEFAULT 0, lakeshore372_temp{}_extrap FLOAT NOT NULL DEFAULT 0'.format(i, i, i)
        create_stmt += ');'
        TABLES['test_db'] = (create_stmt)
      
        # execute
        cursor = self._cnx.cursor()
        for name, ddl in TABLES.items():
            try:    
                print('Creating table {}: '.format(name), end = '')
                #cursor.execute('DROP TABLE test_db;')
                cursor.execute(ddl)
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    print ('already exists.')
                else:
                    print (err.msg)
            else:
                print('Table successfully created!')
        
        cursor.close()  
        return True
   """

                                             
    
    def insert(self, table_name, data_dict,add_datetime=False):
    
        '''
        # sanity checks
        if self._cnx is None:
            print('Not connected to any database!')
            return False
        '''

        # get columns
        columns = list(data_dict.keys())
      
        # create insert command
        insert_cmd = 'INSERT INTO {} ('.format(table_name)
        
        if add_datetime:
            insert_cmd+='datetime,'

        # add keys
        for key in columns:
            insert_cmd+= '{},'.format(key)
        insert_cmd =  insert_cmd[0:len(insert_cmd)-1]

        # add values
        insert_cmd += ') VALUES ('

        if add_datetime:
            insert_cmd+='NOW(),'

        for key in columns:
            if type(data_dict[key]) == str:
                insert_cmd+= '"{}",'.format(data_dict[key])
            else:
                insert_cmd+= '{},'.format(data_dict[key])
            
        insert_cmd =  insert_cmd[0:len(insert_cmd)-1]
        insert_cmd += ');'
           
        #print(insert_cmd)
        
        # insert database
        cursor = self._cnx.cursor()
        try:    
            cursor.execute(insert_cmd)
            self._cnx.commit()
        except mysql.connector.Error as err:
            print (err.msg)
                       
        cursor.close()

        # done
        return True




    def print(self, table_name):
        
        # sanity checks
        if self._cnx is None:
            print('Not connected to any database!')
            return False

        # select statement
        select_stmt = 'SELECT * from {};'.format(table_name)
        
        # access database
        cursor = self._cnx.cursor()
        try:    
            cursor.execute(select_stmt)
            for x in cursor:
                print(x)
        except mysql.connector.Error as err:
            print (err.msg)
                       
        cursor.close()
        
        
        
    

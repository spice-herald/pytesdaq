from __future__ import print_function
import mariadb
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
                self._cnx = mariadb.connect(user=self._user, password=self._password,
                                                    host=self._host, port=self._port,
                                                    database=self._dbname)
            except mariadb.Error as err:
                if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                    print('Something is wrong with your user name or password')
                elif err.errno == errorcode.ER_BAD_DB_ERROR:
                    print('Database does not exist')
                else:
                    print(err)
            else:
                print('Database successfully connected!')
        return True

    def connect_test(self): # localhost database for now, update with actual database later
        self.connect_manual(host='sequoia.dyn.berkeley.edu', port=3306, user='daquser_hdf5', password='RznY_23')
#192.168.1.177

    def disconnect(self):
        if self._cnx is None:
            print('Not connected to any database!')
            return False
        self._cnx.close()
        self._cnx = None
        print('Database successfully disconnected.')



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
            except mariadb.Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    print ('already exists.')
                else:
                    print (err.msg)
            else:
                print('Table successfully created!')

        cursor.close()
        return True
   """



    def insert(self, table_name, data_dict, add_datetime=False):

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
        except mariadb.Error as err:
            print (err.msg)

        cursor.close()

        # done
        return True

    def modify(self, table_name, data_dict, add_datetime=False):

        '''
        # sanity checks
        if self._cnx is None:
            print('Not connected to any database!')
            return False
        '''

        # get columns
        columns = list(data_dict.keys())

        # create insert command
        insert_cmd = 'REPLACE INTO {0} ('.format(table_name)

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

        # update database
        cursor = self._cnx.cursor()
        try:
            cursor.execute(insert_cmd)
            self._cnx.commit()
        except mariadb.Error as err:
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
        print_stmt = 'SELECT * FROM {};'.format(table_name)

        # access database
        cursor = self._cnx.cursor()
        try:
            cursor.execute(print_stmt)
            for x in cursor:
                print(x)
        except mariadb.Error as err:
            print (err.msg)

        cursor.close()

    def query(self, table_name, values=[], key=[]): #key = [column, rowval]
        
        # sanity checks
        if self._cnx is None:
            print('Not connected to any database!')
            return False
        
        # select statement
        if values == []:
            select_stmt = 'SELECT * from {0};'.format(table_name)
        else:
            val = ",".join(values)
            select_stmt = 'SELECT {0} from {1};'.format(val, table_name)
            
        if key:
            column, rowval = key
            select_stmt = 'SELECT * from {0} WHERE {1}={2};'.format(table_name, column, rowval)
        # access database
        cursor = self._cnx.cursor()
        result = []
        try:    
            cursor.execute(select_stmt)
            for x in cursor:
                desc = cursor.description
                column_names = [col[0] for col in desc]
                result = [dict(zip(column_names, row))  
                    for row in cursor]
        except mariadb.Error as err:
            print (err.msg)
                       
        cursor.close()
        
        return result
    
    def get_last(self, table_name):
        
        # sanity checks
        if self._cnx is None:
            print('Not connected to any database!')
            return False
        
        print_stmt = "SELECT right(series_num, 14) FROM {0} WHERE right(series_num, 14) =(SELECT max(right(series_num, 14)) FROM {0});".format(table_name)
        
        # access database
        cursor = self._cnx.cursor()
        result = []
        try:    
           
        # print statement
            
            cursor.execute(print_stmt)
            for x in cursor:
                if x == 'NULL': result = None
                else: result = x
        except mariadb.Error as err:
            print (err.msg)
                       
        cursor.close()
        
        return result[0]
        
    


# Useful code to add hdf5 file to database
def add_to_db(info): # info is hdf5 file that's been read by python into a dict

    # gather data we want to insert
    nameset = ['series_num', 'run_type', 'timestamp', 'comment'] # data that is present in hdf5 test file
    dataset = {}
    for name in nameset:
        dataset[name] = info[name]
    dataset['nb_events']=info['adc1']['nb_events'] # nb_events not in main
                                                    # part of dictionary

    # create server object (assumes the server includes a databse called 'tesdaq')
    server = MySQLCore()

    # connect to tesdaq database
    # password changes depending on server, but port and user should stay the same

    server.connect_manual(host="localhost", port=3306, user="root", password="password123")

    # insert data into "test_data" table (insert whatever table name is needed)
    server.insert("test_data", dataset)

    # test_data SQL table initialized with the following data types:

        # id → INT
        # series_name → VARCHAR(40)
        # series_num → BIGINT
        # facility_num → INT
        # fridge_run → INT
        # run_type → INT
        # run_mode → VARCHAR(40)
        # timestamp → BIGINT
        # nb_events → INT
        # nb_dumps → INT
        # comment → VARCHAR(512)
        # user_comment → VARCHAR(512)

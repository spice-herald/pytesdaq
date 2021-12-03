import os
import sys
import stat
import re

def build_range_str(data_list):
    """ 
    Takes a list of numbers between a and b inclusive and build a string with
    comma separated ranges like "a-b,c-d,f", numbers from a to b, a to d and f
    """
    data_list.sort()
    units = []
    prev_val = data_list[0]
    
    for val in data_list:
        if val == prev_val+1:
            units[-1].append(val)
        else:
            units.append([val])
        prev_val = val
   
    return '_'.join(['{0}-{1}'.format(u[0],u[-1]) if len(u)>1 else str(u[0]) for u in  units])



def hyphen_range(data_str):   
    """ 
    Takes a range in form of "a-b" and generate a list of numbers between a and b inclusive.
    Also accepts comma separated ranges like "a-b,c-d,f" will build a list which will include
    Numbers from a to b, a to d and f
    """
    data_str="".join(data_str.split()) #removes white space
    data_str = data_str.replace(',','_') # in case ',' format used
    r=set()

    for x in data_str.split('_'):
        t=x.split('-')
        if len(t) not in [1,2]: raise SyntaxError('hash_range is given its arguement as '
                                                  + data_str.replace('_',',')
                                                  + ' which seems not correctly formated!')
        r.add(int(t[0])) if len(t)==1 else r.update(set(range(int(t[0]),int(t[1])+1)))
        data_list=list(r)

    data_list.sort()
    return data_list



def make_directories(directories):
    """
    Create directory
    """
    
    if not isinstance(directories, list):
        directories = [directories]
        

    for dir_name in directories:
        if not os.path.isdir(dir_name):
            try:
                os.makedirs(dir_name)
                os.chmod(dir_name,
                         stat.S_IRWXG | stat.S_IRWXU | stat.S_IROTH | stat.S_IXOTH)
            except OSError:
                raise ValueError('\nERROR: Unable to create directory "'
                                 + dir_name + '"!\n')
              
          

def extract_list(arg_list):
    """
    Extract input list,
    separations are comma and space
    """

    # check if list
    if not isinstance(arg_list, list):
        arg_list = [arg_list]

    output_list = list()
    for item in arg_list:
        item_list = re.split('\s|,|;', item.strip())
        for item_split in item_list:
            if item_split:
                output_list.append(item_split)
                
    return output_list
        
    

"""
阿里云核心SDK库：pip3 install aliyun-python-sdk-core
阿里云域名SDK库：pip3 install aliyun-python-sdk-domain
阿里云DNSSDK库：pip3 install aliyun-python-sdk-alidns
"""
import os
import time
import urllib.request
# from lxml import etree
from aliyunsdkcore.client import AcsClient
# from aliyunsdkcore.acs_exception.exceptions import ClientException
# from aliyunsdkcore.acs_exception.exceptions import ServerException
from datetime import datetime
from aliyunsdkalidns.request.v20150109 import DescribeSubDomainRecordsRequest, AddDomainRecordRequest, UpdateDomainRecordRequest, DeleteDomainRecordRequest
import json, urllib
import yaml
import os.path as osp


CONFIG_FILE = "config.yaml"
REGION_ID = 'cn-hangzhou'
TTL = 600

if not osp.isfile(CONFIG_FILE):
    cfg = {
        "default": {
            "regionID": REGION_ID,
            "ttl": TTL,
            "id": "your_id",
            "key": "your_key"
        },
        "tasks": [
            {
                "domain": "your_ipv4_domain.com",
                "record_type": "A",
                "record_value": "www"
            },
            {
                "domain": "your_ipv6_domain.com",
                "record_type": "AAAA",
                "record_value": "ipv6.www",
                "interface": "eth0",
                "index": 1
            }
        ]
    }
    yaml.dump(cfg, open(CONFIG_FILE, "w"), yaml.Dumper, sort_keys=False)
    print(f'modify {osp.abspath(CONFIG_FILE)} and then restart this code')
    exit(0)
else:
    cfg = yaml.load(open(CONFIG_FILE, "r"), yaml.Loader)
    REGION_ID = cfg["default"]["regionID"]
    TTL = cfg["default"]["ttl"]


# 获取所属公网ip
def get_outside_ip(*args):
    with urllib.request.urlopen('https://www.3322.org/dyndns/getip') as response:
        ip = (response.read()).decode().rstrip('\n')
    return ip


def get_ipv6_ip(now_index=0):
    interface = cfg["tasks"][now_index]["interface"]
    idx = cfg["tasks"][now_index]["index"]
    flag = False
    count = 0
    ip_str = ""
    for line in os.popen("ifconfig").read().split("\n"):
        
        if "flags" in line and "mtu" in line:
            flag = interface in line
            count = 0
                
        elif flag and "inet6" in line:
            # print(line, flag)
            if count == idx:
                ip_str = line.split()[1]
                break
            count += 1
    
    return ip_str
    
    

class DDNS(object):

    __regionId = REGION_ID
    __task = {}
    __delay = TTL

    def __init__(self):
        self.__ID = cfg["default"]["id"]
        self.__SECRET = cfg["default"]["key"]
        self.__client = AcsClient(self.__ID, self.__SECRET, self.__regionId)

    @staticmethod
    def __write_to_log(msg, write=True):
        log_file_name = 'log.txt'
        if os.path.exists(log_file_name):
            string = open(log_file_name).read()
        else:
            string = ''
        print('[%s] %s' % (str(datetime.now()).split('.')[0], msg))
        if write:
            open(log_file_name, 'w').write('%s[%s] %s\n' % (string, str(datetime.now()).split('.')[0], msg))

    # 查询记录
    def __getDomainInfo(self, SubDomain):
        request = DescribeSubDomainRecordsRequest.DescribeSubDomainRecordsRequest()
        request.set_accept_format('json')
        request.set_SubDomain(SubDomain)
        response = self.__client.do_action_with_exception(request)
        response = str(response, encoding='utf-8')
        return json.loads(response)

    # 更新记录
    def __updateDomainRecord(self, address, rr, record_id, address_type='A'):
        request = UpdateDomainRecordRequest.UpdateDomainRecordRequest()
        request.set_accept_format('json')

        request.set_Priority('1') if address_type == 'MX' else None
        request.set_TTL('600')
        request.set_Value(address) 
        request.set_Type(address_type)
        request.set_RR(rr)
        request.set_RecordId(record_id) 

        response = self.__client.do_action_with_exception(request)
        response = str(response, encoding='utf-8')
        return response

    def __ddns_for_one_record(self, DomainName, RR, address_source, msg, address_type='A', idx=0):
        SubDomain = '%s.%s' % (RR, DomainName) if not RR == '@' else DomainName   # 子域名
        real_address = address_source(idx)                                         # 实际IP

        for this_record in msg['DomainRecords']['Record']:
            if this_record['Type'] == address_type:
                now_web_address = this_record['Value']                          # 阿里云记录的IP
                recordID = this_record["RecordId"]                              # 该条记录的ID
                if not now_web_address == real_address:                         # 如果IP变化则更改该条记录
                    self.__write_to_log('ip of %s changed from %s to %s, ddns service start' % (SubDomain, now_web_address, real_address))
                    returnmsg = self.__updateDomainRecord(real_address, RR, recordID, address_type)
                    self.__write_to_log('msg of %s from aliyun: %s' % (SubDomain, returnmsg))
                else:
                    self.__write_to_log('ip of %s not changed' % SubDomain, False)
                return True
            else:
                return False

    def __ddns_for_one_subdomain(self, DomainName, RR):
        SubDomain = '%s.%s' % (RR, DomainName) if not RR == '@' else DomainName
        print(SubDomain)
        msg = self.__getDomainInfo(SubDomain)
        print(msg)
        for i in range(self.__task[DomainName][RR]['totalCount']):
            address_source = self.__task[DomainName][RR]['address_source'][i]
            address_type = self.__task[DomainName][RR]['address_type'][i]
            index = self.__task[DomainName][RR]['index']
            if not self.__ddns_for_one_record(DomainName, RR, address_source, msg, address_type, index):
                self.__write_to_log('%s has no record with type of %s' %(DomainName, address_type))

    def __ddns_for_once(self):
        for DomainName in self.__task:
            for RR in self.__task[DomainName]:
                self.__ddns_for_one_subdomain(DomainName, RR)


    ####################################################################################################################

    def add_task(self, DomainName, RR, address_source, address_type, idx):
        if DomainName not in self.__task:
            self.__task[DomainName] = {}
        if RR not in self.__task[DomainName]:
            self.__task[DomainName][RR] = {'address_source': [], 'address_type': [], 'totalCount': 0}
        flag1 = address_source not in self.__task[DomainName][RR]['address_source']
        flag2 = address_type not in self.__task[DomainName][RR]['address_type']
        if flag1 and flag2:
            self.__task[DomainName][RR]['address_source'].append(address_source)
            self.__task[DomainName][RR]['address_type'].append(address_type)
            self.__task[DomainName][RR]['totalCount'] += 1
            self.__task[DomainName][RR]['index'] = idx

    def get_all_task(self):
        return self.__task

    def set_delay(self, hours=0, minutes=0, seconds=0):
        self.__delay = hours*3600 + minutes*60 + seconds

    def start_service(self, ):
        while True:
            try:
                self.__ddns_for_once()
            except:
                pass
            time.sleep(self.__delay)


if __name__ == '__main__':
    my_ddns = DDNS()

    for i, v in enumerate(cfg["tasks"]):
        my_ddns.add_task(
            DomainName=v["domain"],                                                                     # 域名
            RR=v["record_value"],                                                                       # 主机记录
            address_source=get_ipv6_ip if v["record_type"] == "AAAA" else get_outside_ip,               # 记录值来源，返回的一定要是字符串
            address_type=v["record_type"],                                                              # 记录类型
            idx=i                                                                                       
        )               

    print(my_ddns.get_all_task())
    my_ddns.set_delay(minutes=TTL / 60)                                     # 每XX分钟查询一次是否有变化
    # my_ddns.set_delay(seconds=TTL)                                        # 每XX秒钟查询一次是否有变化
    # my_ddns.set_delay(hours=TTL / 3600)                                   # 每XX小时查询一次是否有变化
    my_ddns.start_service()                                                 # 开始服务

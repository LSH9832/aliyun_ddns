"""
阿里云核心SDK库：pip3 install aliyun-python-sdk-core
阿里云域名SDK库：pip3 install aliyun-python-sdk-domain
阿里云DNSSDK库：pip3 install aliyun-python-sdk-alidns
"""
import os
import time
import urllib.request
from lxml import etree
from aliyunsdkcore.client import AcsClient
# from aliyunsdkcore.acs_exception.exceptions import ClientException
# from aliyunsdkcore.acs_exception.exceptions import ServerException
from datetime import datetime
from aliyunsdkalidns.request.v20150109 import DescribeSubDomainRecordsRequest, AddDomainRecordRequest, UpdateDomainRecordRequest, DeleteDomainRecordRequest
import json, urllib


# 获取所属公网ip
def get_outside_ip():
    with urllib.request.urlopen('https://www.3322.org/dyndns/getip') as response:
        ip = (response.read()).decode().rstrip('\n')
    return ip


class DDNS(object):

    __regionId = 'cn-hangzhou'
    __task = {}
    __delay = 600

    def __init__(self, ID, SECRET):
        self.__ID = ID
        self.__SECRET = SECRET
        self.__client = AcsClient(ID, SECRET, self.__regionId)

    @staticmethod
    def __write_to_log(msg):
        log_file_name = 'log.txt'
        if os.path.exists(log_file_name):
            string = open(log_file_name).read()
        else:
            string = ''
        print('[%s] %s' % (str(datetime.now()).split('.')[0], msg))
        open(log_file_name, 'w').write('%s[%s] %s\n' % (string, str(datetime.now()).split('.')[0], msg))

    # 查询记录
    def __getDomainInfo(self, SubDomain):
        request = DescribeSubDomainRecordsRequest.DescribeSubDomainRecordsRequest()
        request.set_accept_format('json')

        # 指定查记的域名 格式为 'test.example.com'
        request.set_SubDomain(SubDomain)

        response = self.__client.do_action_with_exception(request)
        response = str(response, encoding='utf-8')

        # 将获取到的记录转换成json对象并返回
        return json.loads(response)

    # 更新记录
    def __updateDomainRecord(self, address, rr, record_id, address_type='A'):
        request = UpdateDomainRecordRequest.UpdateDomainRecordRequest()
        request.set_accept_format('json')

        request.set_Priority('1') if address_type == 'MX' else None
        request.set_TTL('600')
        request.set_Value(address)          # 指向的新的地址（A:ipv4地址，AAAA:ipv6地址）
        request.set_Type(address_type)
        request.set_RR(rr)
        request.set_RecordId(record_id)     # 更新记录需要指定 record_id ，该字段为记录的唯一标识，可以在获取方法的返回信息中得到该字段的值

        response = self.__client.do_action_with_exception(request)
        response = str(response, encoding='utf-8')
        return response

    def __ddns_for_one_record(self, DomainName, RR, address_source, msg, address_type='A'):
        SubDomain = '%s.%s' % (RR, DomainName) if not RR == '@' else DomainName   # 子域名
        real_address = address_source()                                         # 实际IP

        for this_record in msg['DomainRecords']['Record']:
            if this_record['Type'] == address_type:
                now_web_address = this_record['Value']                          # 阿里云记录的IP
                recordID = this_record["RecordId"]                              # 该条记录的ID
                if not now_web_address == real_address:                         # 如果IP变化则更改该条记录
                    self.__write_to_log('ip of %s changed from %s to %s, ddns service start' % (SubDomain, now_web_address, real_address))
                    returnmsg = self.__updateDomainRecord(real_address, RR, recordID, address_type)
                    self.__write_to_log('msg of %s from aliyun: %s' % (SubDomain, returnmsg))
                else:
                    self.__write_to_log('ip of %s not changed' % SubDomain)
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
            if not self.__ddns_for_one_record(DomainName, RR, address_source, msg, address_type):
                self.__write_to_log('%s has no record with type of %s' %(DomainName, address_type))

    def __ddns_for_once(self):
        for DomainName in self.__task:
            for RR in self.__task[DomainName]:
                self.__ddns_for_one_subdomain(DomainName, RR)


    ####################################################################################################################

    def add_task(self, DomainName, RR, address_source, address_type):
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
    my_ID = '此处填入你的阿里云的ID'
    my_SECRET = '此处填入你的阿里云的KEY'
    
    # 以下四个列表内容一一对应填入
    my_DomainNames = ['your_first_website_name.com', 'www.your_second_website_name.com']
    my_RRs = ['@', 'www']
    my_ip_sources = [get_outside_ip, get_outside_ip]
    my_Record_Types = ['A', 'A']

    my_ddns = DDNS(ID=my_ID, SECRET=my_SECRET)

    for my_DomainName, my_RR, my_ip_source, my_Record_Type in zip(my_DomainNames, my_RRs, my_ip_sources, my_Record_Types):
        my_ddns.add_task(DomainName=my_DomainName,                  # 域名
                         RR=my_RR,                                  # 主机记录
                         address_source=my_ip_source,               # 记录值来源，返回的一定要是字符串
                         address_type=my_Record_Type)               # 记录类型

    print(my_ddns.get_all_task())
    my_ddns.set_delay(minutes=10)                                   # 每10分钟查询一次是否有变化
    # my_ddns.set_delay(seconds=10)                                 # 每10秒钟查询一次是否有变化
    # my_ddns.set_delay(hours=10)                                   # 每10小时查询一次是否有变化
    my_ddns.start_service()                                         # 开始服务

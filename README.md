# 使用Python脚本实现在阿里云注册的域名的DDNS解析


## 1.下载本项目
```
git clone https://github.com/LSH9832/aliyun_ddns.git
```

## 2.安装依赖库
```
pip3 install -r requirements.txt
```

## 3.配置
打开main.py<br>
如果不是对公网ip进行解析，就把ip的获取方式的函数"get_outside_ip"以及获取ipv6地址的函数"get_ipv6_ip"改了。<br>
然后运行脚本
```
python main.py
```
首次运行自动生成配置文件config.yaml
```yaml
default:
  id: your_ip
  key: your_key
  regionID: cn-hangzhou
  ttl: 600
tasks:
- domain: your_ipv4_domain.com
  record_type: A
  record_value: www
- domain: your_ipv6_domain.com
  record_type: AAAA
  record_value: ipv6.www
  interface: eth0
  index: 1
```
修改相应配置，再次运行脚本即可开始ddns服务。

## 4.运行
1.直接运行py文件即可。<br>
2.如果是linux服务器，可以将main.py文件写进一个service文件中，设置开机自启动。<br>
3.可以在生成的log.txt文件中查看ip变更信息

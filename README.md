# 使用Python脚本实现在阿里云注册的域名的DDNS解析
要求**python=3.X**
## 1.安装阿里云第三方库
```
pip3 install aliyun-python-sdk-core
pip3 install aliyun-python-sdk-domain
pip3 install aliyun-python-sdk-alidns
```

## 2.下载本项目
```
git clone https://github.com/LSH9832/aliyun_ddns.git
```

## 3.配置
打开main.py<br>
如果不是对公网ip进行解析，就把ip的获取方式的函数"get_outside_ip"改了。<br>
然后找到脚本最下面
```
if __name__ == '__main__':
```
里面，把相关域名信息还有你自己的ID和KEY填进去即可。<br>
代码很简单，看看怎么写的就会改了，无需多言。

## 4.运行
1.直接运行py文件即可。<br>
2.如果是linux服务器，可以将main.py文件写进一个service文件中，设置开机自启动。

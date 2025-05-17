import os
import requests
import json
from bs4 import BeautifulSoup
import re

# Cloudflare API配置信息
CF_API_KEY = os.getenv('CF_API_KEY')
CF_ZONE_ID = os.getenv('CF_ZONE_ID')
CF_DOMAIN_NAME = os.getenv('CF_DOMAIN_NAME')
CF_API_EMAIL = os.getenv('CF_API_EMAIL')

# 定义请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 定义网址列表
urls = [
    "https://cf.090227.xyz/",
    "https://stock.hostmonit.com/CloudFlareYes",
    "https://ip.164746.xyz/",
    "https://monitor.gacjie.cn/page/cloudflare/ipv4.html"
]

# 解析延迟数据的正则表达式
latency_pattern = re.compile(r'(\d+(\.\d+)?)\s*(ms|毫秒)?')

# 提取表格数据的函数
def extract_table_data(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 检查请求是否成功
        return BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {url}, 错误: {e}")
        return None

# 处理每个网址的数据
def process_site_data(url):
    soup = extract_table_data(url)
    if not soup:
        return []

    data = []
    
    if "cf.090227.xyz" in url:
        rows = soup.find_all('tr')
        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 3:
                line_name = columns[0].text.strip()
                ip_address = columns[1].text.strip()
                latency_text = columns[2].text.strip()
                latency_match = latency_pattern.search(latency_text)
                if latency_match:
                    latency_value = latency_match.group(1)
                    data.append(f"{ip_address}#{line_name}-{latency_value}ms")

    elif "stock.hostmonit.com" in url:
        rows = soup.find_all('tr', class_=re.compile(r'el-table__row'))
        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 3:
                line_name = columns[0].text.strip()
                ip_address = columns[1].text.strip()
                latency_text = columns[2].text.strip()
                latency_match = latency_pattern.search(latency_text)
                if latency_match:
                    latency_value = latency_match.group(1)
                    data.append(f"{ip_address}#{line_name}-{latency_value}ms")

    elif "ip.164746.xyz" in url:
        rows = soup.find_all('tr')
        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 5:
                ip_address = columns[0].text.strip()
                latency_text = columns[4].text.strip()
                latency_match = latency_pattern.search(latency_text)
                if latency_match:
                    latency_value = latency_match.group(1)
                    data.append(f"{ip_address}-{latency_value}ms")

    elif "monitor.gacjie.cn" in url:
        rows = soup.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 5:
                line_name = tds[0].text.strip()
                ip_address = tds[1].text.strip()
                latency_text = tds[4].text.strip()
                latency_match = latency_pattern.search(latency_text)
                if latency_match:
                    latency_value = latency_match.group(1)
                    data.append(f"{ip_address}#{line_name}-{latency_value}ms")

    return data

# 验证IP地址格式
def is_valid_ip(ip):
    pattern = re.compile(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
    return bool(pattern.match(ip))

# 清空CF_DOMAIN_NAME的所有DNS记录
def clear_dns_records():
    print("开始清空DNS记录...")
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records?name={CF_DOMAIN_NAME}"
    headers = {
        "Authorization": f"Bearer {CF_API_KEY}",
        "X-Auth-Email": CF_API_EMAIL,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        records = response.json().get('result', [])
        if not records:
            print("没有找到需要删除的DNS记录")
            return
            
        for record in records:
            delete_url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/{record['id']}"
            delete_response = requests.delete(delete_url, headers=headers)
            if delete_response.status_code == 200:
                print(f"成功删除DNS记录: {record['name']} ({record['id']})")
            else:
                error_info = delete_response.json().get('errors', [{}])[0].get('message', '未知错误')
                print(f"删除失败: {record['name']} ({record['id']}), 状态码: {delete_response.status_code}, 错误: {error_info}")
                
    except requests.exceptions.RequestException as e:
        print(f"清空DNS记录请求失败: {e}")
    except (KeyError, json.JSONDecodeError) as e:
        print(f"解析API响应失败: {e}")

# 添加新的IPv4地址为DNS记录
def add_dns_record(ip):
    if not is_valid_ip(ip):
        print(f"无效的IP地址: {ip}，跳过添加")
        return
        
    print(f"正在添加DNS记录: {ip}")
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
    headers = {
        "Authorization": f"Bearer {CF_API_KEY}",
        "X-Auth-Email": CF_API_EMAIL,
        "Content-Type": "application/json"
    }
    data = {
        "type": "A",
        "name": CF_DOMAIN_NAME,
        "content": ip,
        "ttl": 60,
        "proxied": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"成功添加DNS记录: {ip}")
    except requests.exceptions.HTTPError as e:
        error_info = response.json().get('errors', [{}])[0].get('message', '未知错误')
        print(f"添加失败: {ip}, 状态码: {response.status_code}, 错误: {error_info}")
    except requests.exceptions.RequestException as e:
        print(f"添加DNS记录请求失败: {e}")
    except (KeyError, json.JSONDecodeError) as e:
        print(f"解析API响应失败: {e}")

# 主函数，处理所有网站的数据
def main():
    print("开始获取Cloudflare IP延迟数据...")
    all_data = []
    
    for url in urls:
        print(f"正在处理: {url}")
        site_data = process_site_data(url)
        all_data.extend(site_data)
        print(f"从{url}获取了{len(site_data)}条IP数据")

    # 去除重复的IP地址行
    unique_data = list(set(all_data))
    print(f"去重后共有{len(unique_data)}条IP数据")

    # 过滤延迟数据低于100ms的行
    try:
        filtered_data = [line for line in unique_data if float(line.split('-')[-1].replace('ms', '')) < 100]
    except (ValueError, IndexError) as e:
        print(f"过滤IP数据时出错: {e}")
        print("使用全部IP数据继续执行...")
        filtered_data = unique_data
        
    print(f"延迟低于100ms的IP共有{len(filtered_data)}条")

    # 写入到yx_ips.txt文件
    if filtered_data:
        with open('yx_ips.txt', 'w', encoding='utf-8') as f:
            for line in filtered_data:
                f.write(line + '\n')
        print(f"已将{len(filtered_data)}条IP数据写入yx_ips.txt")
    else:
        print("没有找到符合条件的IP，程序将退出")
        return

    # 从yx_ips.txt文件中提取IPv4地址
    with open("yx_ips.txt", "r") as file:
        ipv4_list = [line.split('#')[0] for line in file if '#' in line]
    
    print(f"准备处理{len(ipv4_list)}个IP地址")
    
    # 执行清空DNS记录的操作
    clear_dns_records()
    
    # 执行添加DNS记录的操作
    for ip in ipv4_list:
        add_dns_record(ip)
    
    print("所有操作已完成!")

if __name__ == "__main__":
    main()

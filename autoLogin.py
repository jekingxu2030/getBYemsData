"""
一、这个模块是用于自动登录网站的
  1.登录网站地址：http://ems.hy-power.net:8114/login
  2.登录元素定位：
     登录账户：WC001，表单位置：<input type="text" class="ant-input css-111zvph" autocomplete="on" placeholder="请输入登录账号" id="form_item_username" value="WC001">
     密码：123456789，表单位置：<input type="password" class="ant-input css-111zvph" autocomplete="on" placeholder="请输入密码" id="form_item_password" value="123456789">
    验证码表单位置：<input type="text" class="ant-input css-111zvph" placeholder="请输入验证码" value="">
     登录表单元素如下：
    <form data-v-e28a0735="" data-v-f94de0b4="" class="ant-form ant-form-horizontal css-111zvph login-form">
  3.验证码获取方法：在登录页面的验证码元素中内置了验证码属性值
  4.验证码所在元素如下：
    <canvas data-v-83eafb9b="" data-v-e28a0735="" id="canvas" class="verify-canvas" width="120" height="40" verificationcode="n6XQ"></canvas>
  5.其中的verificationcode属性值就是验证码的值
  6.填充账户、密码、验证码后提交登录表单
  7.登录后将服务器设置在本地的cookie和section，以及其他服务器传来的参数全部读出输出
  备注：AI分析用什么语言合适就用什么语言开发代码，登录时间需要延长点，登录窗口可以保持开启；
二、等待设计  
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import json

# === 初始化 Chrome 浏览器（可视窗口） ===
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")  # 启动最大化
# options.add_argument('--headless')  # 如不需要可视界面可开启
driver = webdriver.Chrome(options=options)

try:
    # === Step 1: 打开登录页面 ===
    driver.get("http://ems.hy-power.net:8114/login")
    time.sleep(13)  # 等待页面资源加载

    # === Step 2: 获取验证码 ===
    canvas = driver.find_element(By.ID, "canvas")
    verification_code = canvas.get_attribute("verificationcode")
    print("[验证码] =", verification_code)

    # === Step 3: 精准输入用户名、密码、验证码 ===
    driver.find_element(By.ID, "form_item_username").clear()
    driver.find_element(By.ID, "form_item_username").send_keys("WC001")

    driver.find_element(By.ID, "form_item_password").clear()
    driver.find_element(By.ID, "form_item_password").send_keys("123456789")

    # 验证码输入框：用 placeholder 定位
    verify_input = driver.find_element(
        By.CSS_SELECTOR, 'input[placeholder="请输入验证码"]'
    )
    verify_input.clear()
    verify_input.send_keys(verification_code)

    # === Step 4: 提交登录表单 ===
    # 登录按钮通常是第一个 form 下的 button
    login_form = driver.find_element(By.CSS_SELECTOR, "form.login-form")
    login_button = login_form.find_element(By.TAG_NAME, "button")
    login_button.click()

    # === Step 5: 登录后延长等待时间（确保跳转完成）===
    time.sleep(10)

    # === Step 6: 获取 Cookie（含 session id）===
    print("\n✅ [Cookies]:")
    cookies = driver.get_cookies()
    for cookie in cookies:
        print(f"{cookie['name']} = {cookie['value']}")

    # === Step 7: 获取 localStorage ===
    print("\n✅ [localStorage]:")
    local_storage = driver.execute_script(
        """
        var items = {};
        for (var i = 0; i < localStorage.length; i++) {
            var key = localStorage.key(i);
            items[key] = localStorage.getItem(key);
        }
        return items;
    """
    )
    print(json.dumps(local_storage, indent=2, ensure_ascii=False))

    # === Step 8: 获取 sessionStorage ===
    print("\n✅ [sessionStorage]:")
    session_storage = driver.execute_script(
        """
        var items = {};
        for (var i = 0; i < sessionStorage.length; i++) {
            var key = sessionStorage.key(i);
            items[key] = sessionStorage.getItem(key);
        }
        return items;
    """
    )
    print(json.dumps(session_storage, indent=2, ensure_ascii=False))

    # === Step 9: 输出当前页面 URL ===
    print("\n✅ [当前页面 URL]:", driver.current_url)

    # === Step 10: 浏览器保持开启，按回车后关闭 ===
    input("\n🟢 登录已完成，按回车键关闭浏览器...")

finally:
    driver.quit()

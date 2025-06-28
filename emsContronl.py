import datetime
from math import e


class ChargeDischargeController:
    def __init__(self,log_callback):
        # 初始化is_charging和is_discharging为False
        self.is_charging = False
        self.is_discharging = False
        # 将log_callback赋值给self.log_callback
        self.log_callback = log_callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)  # 调用回调函数输出日志  

    def send_cmd(self,value):
        from ems_websocket_client import WebSocketWorker  # 导入 WebSocketWorker 类
        self.ws_worker = WebSocketWorker()  # 创建 WebSocketWorker 实例
        self.ws_worker.start()  # 启动工作线程

        cmd_id = 2409001129
        ref_fid = 409012
        ref_rid = 1     #设置PCS工作
        # value = 1
        # 调用 WebSocketWorker 的 send_cmd_subscription 方法
        self.ws_worker.send_cmd_subscription(cmd_id, ref_fid, ref_rid, value)          

    def monitor_charge_discharge(self, soc, charging_start_time, charging_end_time, discharging_start_time, discharging_end_time, soc_upper_limit, soc_lower_limit,runModel):
        current_time = datetime.datetime.now().time()  # 获取当前时间
        current_hour = datetime.datetime.now().hour  # 获取当前小时
        
        # controller = ChargeDischargeController(log_callback=self.log)



          # 处理充电时间段跨午夜的情况
        if charging_end_time < charging_start_time:
           charging_end_time += 23

         # 处理放电时间段跨午夜的情况
        if discharging_end_time < discharging_start_time:
           discharging_end_time += 23

         # 处理跨午夜的当前时间
        # if current_hour < charging_start_time:
        #    current_hour += 23

        # 测试被调用传入参数打印
        print("系统运行模式:", runModel)
        print("当前SOC值:", soc)
        print("充电开始时间:", charging_start_time)
        print("充电结束时间:", charging_end_time)
        print("放电开始时间:", discharging_start_time)
        print("放电结束时间:", discharging_end_time)
        print("SOC上限:", soc_upper_limit)
        print("SOC下限:", soc_lower_limit)
        print("当前时间:", current_hour)
         
        self.log(f"SOC上限:{soc_upper_limit}") 
        self.log(f"SOC下限:{soc_lower_limit}") 
        self.log(f"当前SOC:{soc}") 
        self.log(f"当前运行模式:{runModel}")
            ## 在这里添加数据判断和处理逻辑
        # if soc > soc_upper_limit:
        #     print("SOC超出上限，需要停止充电")
        # elif soc < soc_lower_limit:
        #     print("SOC超出下限，需要停止放电或充电")
        # else:
        #     print("SOC范围正常！")
        


        # 判断是否在充电时间段内
        if charging_start_time <= current_hour <= charging_end_time:  
            print("当前在充电时间段内，判断是否需要充电")

            if soc >= soc_upper_limit:  ## 如果当前SOC大于等于上限
                print("当前SOC已达到上限，停止充电")

                # controller.send_cmd(value=0)  # 发送命令
                # self.stop_charging()  # 停止充电
            elif not self.is_charging:  # 如果当前不在充电
                # self.start_charging()  # 启动充电
                print("当前SOC未达到上限，启动充电")    
                if self.is_charging:
                     print("本身在充电")
                     return
                else:
                #   self.send_cmd(value=2)
                  self.is_charging = True
                  print("开始充电")
                # controller.send_cmd(value=1)  # 发送命令
                
            else:
                print("继续充电")

        # # 判断是否在放电时间段内
        elif discharging_start_time <= current_hour <= discharging_end_time: 
            print("当前在放电时间段内，判断是否需要放电") 
            if soc <= soc_lower_limit:  ## 如果当前SOC小于等于下限
                print("当前SOC已达到下限，停止放电")
                # controller.send_cmd(value=0)  # 发送命令
                # self.stop_discharging()  # 停止充电
            elif not self.is_discharging:  # 如果当前不在放电
                # self.start_discharging()  # 启动放电
                print("当前SOC未达到下限，启动放电") 
                # controller.send_cmd(value=-1)  # 发送命令   
            else:
                print("继续放电")
        else:
            print("当前不在充电或放电时间段内")        


    

    # def start_charging(self):
    #     if self.is_charging:
    #         return
    #     else:
    #         self.send_cmd(value=1)
    #     self.is_charging = True
    #     print("开始充电")

    # def stop_charging(self):
    #     if not self.is_charging:
    #         return
    #     else:
    #         self.send_cmd(value=0)
    #     self.is_charging = False
    #     print("停止充电")

    # def start_discharging(self):
    #     if self.is_discharging:
    #         return  
    #     else:
    #         self.send_cmd(value=-1)
    #     self.is_discharging = True
    #     print("开始放电")

    # def stop_discharging(self):
    #     if not self.is_discharging:
    #         return
    #     else:
    #         self.send_cmd(value=0)  
    #     self.is_discharging = False
    #     print("停止放电")

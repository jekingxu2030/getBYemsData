-- 删除原有触发器
-- 1️⃣ 删除已有触发器
DROP TRIGGER IF EXISTS trg_device_data_summary_before_insert;

-- 2️⃣ 创建新触发器
DELIMITER //

CREATE TRIGGER trg_device_data_summary_before_insert
BEFORE INSERT ON device_data_summary
FOR EACH ROW
BEGIN
    -- 如果 created_at_ms 为空，则使用荷兰当地时间生成毫秒时间戳
    IF NEW.created_at_ms IS NULL THEN
        -- CONVERT_TZ: 将当前服务器时间转换为荷兰时间 (+02:00)
        -- UNIX_TIMESTAMP: 转成秒，再乘以1000得到毫秒
        SET NEW.created_at_ms = UNIX_TIMESTAMP(CONVERT_TZ(NOW(3), @@session.time_zone, '+02:00')) * 1000;
    END IF;
END;
//

DELIMITER ;

-- 3️⃣ 测试插入
-- INSERT INTO device_data_summary (other_columns…) VALUES (...);
-- 然后查询：
-- SELECT FROM_UNIXTIME(created_at_ms/1000) AS created_at_nl FROM device_data_summary;


DELIMITER ;

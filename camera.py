import cv2

# 1. 创建摄像头对象，参数0表示默认摄像头[reference:0][reference:1]
#    如果有多个摄像头，可以尝试1, 2...
cap = cv2.VideoCapture(0)

# 2. 检查摄像头是否成功打开[reference:2]
if not cap.isOpened():
    print("错误：无法打开摄像头")
    exit()

print("摄像头已成功打开。按 'q' 键退出。")

# 3. 循环读取并显示视频帧
while True:
    # 逐帧捕获
    # ret为布尔值，表示是否成功读取；frame为当前帧的图像数据[reference:3]
    ret, frame = cap.read()
    
    # 如果读取失败，则退出循环[reference:4]
    if not ret:
        print("错误：无法获取视频帧")
        break

    # 显示当前帧
    cv2.imshow('Camera Demo', frame)

    # 等待按键输入，如果按下 'q' 键则退出循环
    # cv2.waitKey(1) 返回按键的ASCII码[reference:5]
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 4. 释放摄像头资源并关闭所有窗口[reference:6]
cap.release()
cv2.destroyAllWindows()
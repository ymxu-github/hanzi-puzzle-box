# 开发人员: ymxu
# 开发时间: 2026/11/2 12:47
# 文件名称: 01-encapsulation.py

"""
封装: 将数据(属性)和操作数据的方法绑定在一起, 形成一个独立的单元(类), 保护数据不被外部访问，通过访问修饰符实现封装。
     1. 私有属性: 在属性名前加双下划线__
     2. 私有方法: 在方法名前加双下划线__
注意事项: Python中是没有真正的私有机制 ;
"""
class Car:
    def __init__(self, brand, model, color, owner):
        self.brand = brand  # 品牌
        self.model = model  # 型号
        self.color = color  # 颜色
        self.__owner = owner # 私有属性，车主

    def start(self):
        print(f'{self.brand} {self.model} is starting.')

    def run(self):
        print(f'{self.__owner}: {self.brand} {self.model} is running.')

    def stop(self):
        print(f'{self.brand} {self.model} is stopping.')

    def __control_fuel(self):
        print(f'{self.__owner}: Controlling fuel for {self.brand} {self.model}.')

    def get_owner(self):
        return self.__owner[0:1] + '***'

if __name__ == '__main__':
    car = Car('Toyota', 'Camry', 'Blue', 'Alice')
    car.start()
    car.run()
    car.stop()
    print(f'Owner: {car.get_owner()}')

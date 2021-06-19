from client_info.video import Clip
class BasicClient:
    def __init__(self,max_buffer,file,tot_num):
        self.max_buffer = max_buffer
        self.video=[]
        for i in range(tot_num):
            self.video.append(Clip(file[i]))
    def get_cur_vido_buffer(self):
        #需要和操作系统结合
        return 1000
        pass





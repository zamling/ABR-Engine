'''
the model of Linear BBA

lower_bound_
'''
from basic import Chunk
from client_info import BasicClient

class BBA:
    def __init__(self,client):
        self.client = client

    def select_video_format(self,num):
        max_buffer = self.client.max_buffer # the maximum buffer size of this device
        video_buffer = self.client.get_cur_vido_buffer()
        remain_buffer = min(max(video_buffer,0),max_buffer)
        video_repre_list = self.client.video[num]
        #self.client.video是一个视频所有Clip的List，每个Clip是可用的chunk的List
        num_chunk_size = len(video_repre_list)
        max_size = 0
        min_size = 1,000,000
        max_id=0
        min_id=0
        for i in range(num_chunk_size):
            chunk_size = video_repre_list[i].size
            if(chunk_size > max_size):
                max_size = chunk_size
                max_id = i
            if(chunk_size < min_size):
                min_size = chunk_size
                min_id = i
        upper_bound_buffer = 800
        lower_bound_buffer = 200
        if(remain_buffer>upper_bound_buffer):
            return max_id,max_size
        elif(remain_buffer <= lower_bound_buffer):
            return min_id,min_size
        slope = (max_size-min_size)/(upper_bound_buffer-lower_bound_buffer)
        '''
        buffer 做横轴，chrunk size做纵轴
        '''
        max_serve_size = min_size + slope*(remain_buffer-lower_bound_buffer)
        max_ssim = -1
        opt_id = 0
        opt_size = video_repre_list[0].size
        for i in range(num_chunk_size):
            chunk_size = video_repre_list[i].size
            ssim = video_repre_list[i].ssim
            if(chunk_size <= max_serve_size):
                #理论上chunk size越大，ssim应该越大
                if(ssim > max_ssim):
                    opt_id = i
                    opt_size=chunk_size
        return opt_id,opt_size

if __name__=="__main__":
    #选择下一个chunk
    file = "/"
    client =BasicClient(1000,file,1)
    abr = BBA(client=client)
    chunk_id,chunk_size = abr.select_video_format(0)





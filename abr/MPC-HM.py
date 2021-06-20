import numpy as np
class MPC:
    def __init__(self,client,pre_chrunk_num,lam,mu,mus,buf_lengh,is_robust=False):
        self.client = client
        self.pre_chunk_num = pre_chrunk_num
        self.lam = lam
        self.mu = mu
        self.mus = mus
        self.past_chrunk = []
        self.is_robust=is_robust
        self.last_tp_pred = 0
        max_buf  = 1000
        self.unit_buf = int(max_buf / buf_lengh)
        self.real_buffer = [] #将buffer重新分段
        for i in range(buf_lengh):
            self.real_buffer.append(i*self.unit_buf)


    def update_past_chruck(self,x):
        err=0
        if self.is_robust and self.last_tp_pred >0:
            err = abs(1-self.last_tp_pred*x.tt/x.size/1000)
        self.past_chrunk.append((x,err))
        if len(self.past_chrunk) > self.pre_chunk_num:
            self.past_chrunk.pop(0)

    def discretize_buffer(self,buf):
        '''
        :param buf:
        :return: the index of real_buffer which corresponding to the buf
        '''
        return round(buf / self.unit_buf)

    def throughput_predictor(self):
        HIGH_SENDING_TIME = 10 #casual value
        past_throughput = []
        max_err = 0
        for i in range(len(self.past_chrunk)):
            thoughput = past_throughput[i][0].tt / past_throughput[i][0].size / 1000
            #这里是throughput的倒数
            past_throughput.append(thoughput)
            max_err = max(max_err, past_throughput[i][1])

        if not self.is_robust:
            max_err = 0
        tmp = 0
        for i in range(len(self.past_chrunk)):
            tmp += past_throughput[i]

        if len(self.past_chrunk)!=0:
            unit_st = tmp / len(self.past_chrunk) #调和平均throughput的倒数
            self.last_tp_pred = 1/unit_st
            return unit_st * (1 + max_err)
        else:
            return HIGH_SENDING_TIME

    def select_video_format(self,num):
        throughput_ = self.throughput_predictor()
        cur_buffer = self.client.get_cur_vido_buffer()
        cur_buffer = self.discretize_buffer(cur_buffer)
        cur_format = self.past_chrunk[-1][0]
        return self.update_value(throughput_,cur_buffer,cur_format,num)

    def update_value(self,throughput,cur_buffer,cur_format,num):
        '''
        :param throughput: predicted throughput 的倒数
        :param cur_buffer: index of real_buffer
        :param cur_format: type: Chrunk
        :param num: the next clip is the client.video[num]
        :return: the index of optimal Chrunk opt_chrunck = client.video[num][best_format]
        '''
        
        #下一个format在第num个clip
        max_qvalue = 0
        best_format = 0
        for next_format in range(num):
            trans_time = throughput*self.client.video[next_format].size
            real_rebuffer = trans_time - self.real_buffer[cur_buffer]
            qvalue = self.client.video[next_format].ssim
            - self.lam * max(0,real_rebuffer)
            - self.mu * abs(cur_format.ssim - self.client.video[next_format].ssim)

            if qvalue > max_qvalue:
                best_format = next_format
                max_qvalue = qvalue
        return best_format


















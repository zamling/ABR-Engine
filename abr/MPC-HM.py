import numpy as np
class MPC:
    def __init__(self,client,pre_chrunk_num,lam,mu,mus,buf_lengh,max_lookahead_horizon=1,is_robust=False):
        self.client = client
        self.pre_chunk_num = pre_chrunk_num
        self.lam = lam
        self.mu = mu
        self.mus = mus
        self.past_chrunk = []
        self.is_robust=is_robust
        self.last_tp_pred = 0
        self.max_lookahead_horizon = max_lookahead_horizon
        self.lookahead_horizon = max_lookahead_horizon
        self.buf_lengh = buf_lengh
        max_buf  = 1000
        self.cur_buffer = max_buf
        self.unit_buf = int(max_buf / buf_lengh)
        self.real_buffer = [] #将buffer重新分段
        for i in range(buf_lengh):
            self.real_buffer.append(i*self.unit_buf)
        max_num_format = 100
        self.cur_ssims = np.zeros((max_lookahead_horizon+1,max_num_format))
        self.reciprocal_tp = np.zeros(max_lookahead_horizon+pre_chrunk_num+1)
        self.tt = np.zeros((max_lookahead_horizon+1,max_num_format))
        #cur_ssims存放的是当前chrunk（第0号位）和之后的max_lookahead_horizon个的ssim


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
        max_err = 0
        # for next_chrunk in range(self.lookahead_horizon):
        for i in range(len(self.past_chrunk)):
            reciprocal_thoughput = self.past_chrunk[i][0].tt / self.past_chrunk[i][0].size / 1000
            #这里是throughput的倒数
            self.reciprocal_tp[i]=reciprocal_thoughput
            max_err = max(max_err, self.past_chrunk[i][1])

        if not self.is_robust:
            max_err = 0

        for i in range(self.lookahead_horizon):
            tmp = 0
            for j in range(len(self.past_chrunk)):
                tmp += self.reciprocal_tp[i+j]

            if len(self.past_chrunk) != 0:
                unit_st = tmp / len(self.past_chrunk)
                if(i==0):
                    #说明当前轮是在预测即将要传的chrunk的throughput
                    self.last_tp_pred = 1/unit_st

                self.reciprocal_tp[i+len(self.past_chrunk)] = unit_st * (1+max_err)
            else:
                self.reciprocal_tp[i + len(self.past_chrunk)] = HIGH_SENDING_TIME




    def greedy_select_video_format(self,num):
        self.throughput_predictor()
        throughput_ = self.reciprocal_tp[len(self.past_chrunk)]
        cur_buffer = self.client.get_cur_vido_buffer()
        cur_buffer = min(self.buf_lengh,self.discretize_buffer(cur_buffer))
        cur_format = self.past_chrunk[-1][0]
        return self.greedy_update_value(throughput_,cur_buffer,cur_format,num)

    def greedy_update_value(self,throughput,cur_buffer,cur_format,num):
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
        for next_format in range(len(self.client.video[num])):
            trans_time = throughput*self.client.video[num][next_format].size
            if len(self.past_chrunk)==0:
                diff = 0
            else:
                diff = abs(cur_format.ssim - self.client.video[num][next_format].ssim)
            real_rebuffer = trans_time - self.real_buffer[cur_buffer]
            qvalue = self.client.video[num][next_format].ssim
            - self.lam * max(0,real_rebuffer)
            - self.mu * diff

            if qvalue > max_qvalue:
                best_format = next_format
                max_qvalue = qvalue
        return best_format

    def beam_select_video_format(self,num,remain_num_chrunk):
        #inital current buffer and required ssim lists
        self.cur_buffer = min(self.buf_lengh, self.discretize_buffer(self.client.buf))
        self.lookahead_horizon = min(self.max_lookahead_horizon,remain_num_chrunk)
        if(len(self.past_chrunk) != 0):
            self.cur_ssims[0][0] = self.past_chrunk[-1][0].ssim

        for i in range(self.lookahead_horizon):
            for j in range(len(self.client.video[num+i])):
                self.cur_ssims[i+1][j] = self.client.video[num+i][j].ssim

        # get a series of throughput
        self.throughput_predictor()
        for i in range(self.lookahead_horizon):
            num_format = len(self.client.video[num + i])

            self.tt[0][0] = self.past_chrunk[-1][0].tt

            for j in range(num_format):
                #第0号位永远都是当前chrunck的特征
                self.tt[i + 1][j] = self.client.video[num + i][j].size * self.reciprocal_tp[i + len(self.past_chrunk)]

        best_format,_ = self.find_best_formats(0,self.cur_buffer,0,num)
        return best_format


    def find_best_formats(self,index, cur_buffer, cur_format,num):
        '''

        :param index: 第n个预测的
        :param cur_buffer: 离散过后buffer的index
        :param cur_format: 当前buffer的index 在cur_ssims和tt中
        :return:
        '''
        if(index == self.lookahead_horizon):
            return cur_format, self.cur_ssims[index][cur_format]

        best_format = 0
        max_qvalue = 0
        for next_format in range(len(self.client.video[num])):
            if len(self.past_chrunk) == 0 and index == 0:
                #起始状态下预测第一个没有卡顿
                diff = 0
            else:
                diff = abs(self.cur_ssims[index][cur_format]-self.cur_ssims[index+1][next_format])
            real_rebuffer = self.tt[index+1][next_format] - self.real_buffer[cur_buffer]

            #卡顿的时间 = 下一个format的tt-当前的buffer size
            next_buffer = min(self.buf_lengh,self.discretize_buffer(max(0,-real_rebuffer))+self.client.video[num+1][next_format].period)
            qvalue = self.cur_ssims[index][cur_format] - \
                     self.lam * diff \
                     - self.mu * max(0,real_rebuffer)
            _,next_best_qvalue = self.find_best_formats(index+1,next_buffer,next_format,num+1)

            qvalue += next_best_qvalue

            if(qvalue > max_qvalue):
                best_format = next_format
                max_qvalue = qvalue

        return best_format, max_qvalue









































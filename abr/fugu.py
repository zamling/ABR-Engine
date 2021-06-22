import numpy as np
from fugu_ttp import TransmissionTimePredictor
'''
modified version of MPC
change throughput predictor to a transmission time predictor which is shown in fugu_ttp.py
'''

class Fugu:
    def __init__(self, client, pre_chrunk_num, lam, mu, mus, unit_buf, max_lookahead_horizon=1, is_robust=False,
                 blur_mean_val=0,blur_std_val=1):
        self.client = client
        self.pre_chunk_num = pre_chrunk_num
        self.lam = lam
        self.mu = mu
        self.mus = mus
        self.past_chrunk = []
        self.is_robust = is_robust
        self.last_tp_pred = 0
        self.max_lookahead_horizon = max_lookahead_horizon
        self.lookahead_horizon = max_lookahead_horizon
        self.dis_sending_time_ = 20
        self.is_all_ban = True

        max_buf = 1000
        self.cur_buffer = max_buf
        self.unit_buf = unit_buf
        self.buf_lengh = self.discretize_buffer(max_buf)
        self.real_buffer = []  # 将buffer重新分段
        for i in range(self.buf_lengh):
            self.real_buffer.append(i * self.unit_buf)
        max_num_format = 100
        self.cur_ssims = np.zeros((max_lookahead_horizon + 1, max_num_format))
        self.reciprocal_tp = np.zeros(max_lookahead_horizon + pre_chrunk_num + 1)
        self.sizes = np.zeros((max_lookahead_horizon + 1, max_num_format))
        self.is_ban = np.zeros((max_lookahead_horizon + 1, max_num_format))
        self.sending_time_prob_ = np.zeros((max_lookahead_horizon + 1, max_num_format,self.dis_sending_time_+1))
        # cur_ssims存放的是当前chrunk（第0号位）和之后的max_lookahead_horizon个的ssim
        self.blur_kernel_size = 21
        self.blur_mean_val = blur_mean_val
        self.blur_std_val = blur_std_val
        self.gaussian_kernel_vals_ = np.array(self.blur_kernel_size)

    def update_past_chruck(self, x):
        self.past_chrunk.append(x)
        if len(self.past_chrunk) > self.pre_chunk_num:
            self.past_chrunk.pop(0)

    def discretize_buffer(self, buf):
        '''
        :param buf:
        :return: the index of real_buffer which corresponding to the buf
        '''
        return round(buf / self.unit_buf)



    def ttp(self,num):
        raw_input = []
        if len(self.past_chrunk)==0:
            for i in range(self.pre_chunk_num):
                raw_input.extend(self.client.get_cur_tcp_info())
                raw_input.extend([0,0])
        else:
            for i in range(self.pre_chunk_num):
                diff = self.pre_chunk_num - len(self.past_chrunk)
                for i in range(diff):
                    raw_input.extend(self.past_chrunk[0].get_all_feas())
                    raw_input.extend([self.past_chrunk[0].size / 1500, self.past_chrunk[0].tt/1000])
                for i in range(len(self.past_chrunk)):
                    raw_input.extend(self.past_chrunk[i].get_all_feas())
                    raw_input.extend([self.past_chrunk[i].size / 1500, self.past_chrunk[i].tt/1000])

        raw_input.extend(self.client.get_cur_tcp_info())
        raw_input.append(0)
        #raw_input的总长为62  （5+2）* 8 + 5 + 1 = 62

        for i in range(1,self.lookahead_horizon+1):
            num_formats = len(self.client.video[num+i-1])
            input = np.array((num_formats,len(raw_input)))
            for j in range(num_formats):
                raw_input[-1] = self.sizes[i][j]
                for k in range(len(raw_input)):
                    input[j][k] = raw_input[k]
            model = TransmissionTimePredictor()
            output = model(input)
            # forward的地方已经经过softmax函数了 loss直接用Cross_Entropy_Loss
            for j in range(num_formats):
                if(self.sizes[i][j]<=0):
                    self.is_ban[i][j] = 1
                    continue
                good_prob = 0

                for k in range(self.dis_sending_time_):
                    tmp = output[j][k]

                    if(tmp < 1e-5):
                        self.sending_time_prob_[i][j][k] = 0
                        continue
                    self.sending_time_prob_[i][j][k] = tmp
                    good_prob += tmp

                self.sending_time_prob_[i][j][self.dis_sending_time_]=1-good_prob
                #最后一位储存的是[9.5-Inf]

                if good_prob < 0.5:
                    self.is_ban[i][j] = 1
                else:
                    self.is_ban[i][j] = 0
                    self.is_all_ban=False


            if(self.is_all_ban):
                self.deal_all_ban(i,num_formats)

        if(self.blur_kernel_size > 0):
            for i in range(1,self.lookahead_horizon+1):
                for j in range(len(self.client.video[num+i-1])):
                    self.blur_probability(i,j)



    def cal_gaussian_values(self):
        gaussian_coefficient = 1 / (self.blur_std_val * np.sqrt(2.0*np.pi))
        right_pos = np.floor(self.blur_kernel_size/2)
        left_pos = right_pos
        for x in range(left_pos,right_pos+1):
            exp_idx = -pow(x-self.blur_mean_val,2) / (2 * pow(self.blur_std_val,2))
            gaussian_val = gaussian_coefficient * np.exp(exp_idx)
            self.gaussian_kernel_vals_[x-left_pos] = gaussian_val

    def blur_probability(self,i,j):
        right = np.floor(self.blur_kernel_size / 2)
        left = -right

        sum_prob = 0
        dim_num = self.dis_sending_time_ + 1 #神经网络output的第二维
        original_prob = []
        for k in range(dim_num):
            original_prob.append(self.sending_time_prob_[i][j][k])
        for k in range(dim_num):
            blurred_value = 0
            for x in range(left,right+1):
                gaussian_index = x + left
                covolute_index = (k+j+dim_num) % dim_num
                blurred_value += self.gaussian_kernel_vals_[gaussian_index] * \
                    original_prob[covolute_index]
            self.sending_time_prob_[i][j][k] = blurred_value
            sum_prob += blurred_value
            for k in range(dim_num):
                self.sending_time_prob_[i][j][k] /= sum_prob



    def deal_all_ban(self,i,num_formats):
        '''

        :param i:
        :param num_formats:
        如果所有的包预计传输时间都大于9.5 s的话，就传size最小的，并且停止递归
        '''
        min_size = np.inf
        min_id = 0
        for j in range(num_formats):
            tmp = self.sizes[i][j]
            if tmp > 0 and min_size > tmp:
                min_size = tmp
                min_id = j
        self.is_ban[i][min_id] = 0
        for k in range(self.dis_sending_time_):
            self.sending_time_prob_[i][min_id][k]=0

        self.sending_time_prob_[i][min_id][self.dis_sending_time_] = 1





    def select_video_format(self, num, remain_num_chrunk):
        # inital current buffer and required ssim lists
        self.cur_buffer = min(self.buf_lengh, self.discretize_buffer(self.client.buf))
        self.lookahead_horizon = min(self.max_lookahead_horizon, remain_num_chrunk)
        if (len(self.past_chrunk) != 0):
            self.cur_ssims[0][0] = self.past_chrunk[-1].ssim
            self.sizes[0][0] = self.past_chrunk[-1].size

        for i in range(self.lookahead_horizon):
            for j in range(len(self.client.video[num + i])):
                self.cur_ssims[i + 1][j] = self.client.video[num + i][j].ssim
                self.sizes[i+1][j] = self.client.video[num+i][j].size

        self.ttp(num)
        best_format, _ = self.find_best_formats(0, self.cur_buffer, 0, num)
        return best_format

    def find_best_formats(self, index, cur_buffer, cur_format, num):
        '''

        :param index: 第n个预测的
        :param cur_buffer: 离散过后buffer的index
        :param cur_format: 当前buffer的index 在cur_ssims和tt中
        :return:
        '''
        if (index == self.lookahead_horizon):
            return cur_format, self.cur_ssims[index][cur_format]

        best_format = 0
        max_qvalue = 0
        for next_format in range(len(self.client.video[num])):
            if(self.is_ban[index+1][next_format]):
                #如果这个format的probability太小了
                continue
            qvalue = self.cur_ssims[index][cur_format]

            if(len(self.past_chrunk) == 0 and index == 0):
                diff = 0
            else:
                diff = abs(self.cur_ssims[index][cur_format] - self.cur_ssims[index + 1][next_format])
            qvalue -= self.lam*diff

            for k in range(self.dis_sending_time_):
                #此处我没有取k=dis_sending_time_的时候，因为我认为sending_time_prob_每个format的最后一个代表的是
                #[9.5,Inf],这样的话之后的 k - cur_buffer就没有意义了
                if(self.sending_time_prob_[index+1][next_format][k] == 0):
                    continue
                rebuffer = k - cur_buffer
                next_buffer = min(max(-rebuffer,0)+self.discretize_buffer(self.client.video[num + 1][
                                  next_format].period),self.buf_lengh)
                rebuffer = max(rebuffer,0)
                real_rebuffer = rebuffer * self.unit_buf

                if(cur_buffer - k == 0):
                    real_rebuffer = rebuffer * self.unit_buf * 0.25
                qvalue -= self.mu * real_rebuffer
                _, next_best_qvalue = self.find_best_formats(index + 1, next_buffer, next_format, num + 1)
                qvalue += self.sending_time_prob_[index+1][next_format][k]*next_best_qvalue
            if (qvalue > max_qvalue):
                best_format = next_format
                max_qvalue = qvalue
        return best_format, max_qvalue



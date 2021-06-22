class Chunk:
    '''
    The clips of video in DASH
    '''
    def __init__(self,ssim,size,tt=-1,cwnd=-1,in_flight=-1,
                 min_rtt=-1,rtt=-1,delivery_rate=-1,period = 1):
        self.ssim = ssim
        self.size = size
        self.tt = tt
        self.cwnd = cwnd
        self.in_flight=in_flight
        self.min_rtt=min_rtt
        self.rtt=rtt
        self.delivery_rate=delivery_rate
        self.period = period
        self.PKT_BYT = 1500

    def get_all_feas(self):
        res = []
        res.append(self.delivery_rate / self.PKT_BYT)
        res.append(self.cwnd)
        res.append(self.in_flight)
        res.append(self.min_rtt / 1000000)
        res.append(self.rtt / 1000000)
        return res


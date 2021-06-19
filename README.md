# ABR-Engine

## DASH

Dynamic Adaptive Streaming over HTTP

MPEG-DASH 协议中只对媒体传输以及媒体组织形式方面的内容进行了规范， 对码率选择算法还没有明确定义。   

首先发送Media Presentation Description， MPD  包括视频时长、 视频分片码率、 视频分片分辨率以及各视频分片的 URL 等。

媒体表示。 一个自适应集合包含多个媒体表示， 每个媒体表示包含相同 媒体内容的多种编码版本， 比如不同的码率、 分辨率、 通道数或者其他 特征。 比如一个媒体表示可以是分辨率 320x240、 码率90kbps， 另一个 媒体表示可以是分辨率 320x240、 码率 180kbps， 这样就可以通过不同 的媒体表示来实现自适应码率。  

1. 基于带宽预测的自适应码率选择算法  

客户端驱动的平滑带宽估计方法：该方法基于视频分片的获取时长（segment fetch time， SFT） 来平滑 HTTP 吞吐量从而检测出带宽的变化情况。 文献使用视频分片的时长（media segment duration， MSD） 与视频分片的获取时长的比值 $\mu$ 来评价网络拥塞和可用带宽情况：  
$$
\mu=MSD /SFT
$$
平均TCP吞吐量可被
$$
ThroughPut=\mu \times bitrate
$$
理想情况下 $\mu=1$表示throughput和bitrate匹配 $\mu > 1$throughput大于码率。

平均 TCP吞吐量大于当前视频分片码率及其更高一级码率之和时可以提高码率 。

$\mu$低于一个阈值时，直接下降码率到小于throughput上



2. 基于缓冲的自适应码率选择算法 

当缓冲区大小介于最大最小阈值之间时， 通过构建缓冲-码率映射函数f(B)选择最佳码率  BBA



基于带宽预测的自适应码率算法依赖带宽预测的准确性， 在网络状况比较平稳的情况下

当视频的最高码率远大于网络可用带宽时， 基于缓冲的算法会造成视频分片码率不合理的来回切换， 影
响用户体验。  （在最高和第二高之间切换）



### 播放器缓冲区动态模型  

缓冲区模型实际上相当于是生产者消费者模型， 下载模块为生产者， 解码模块为消费者。输入速率为实际可用带宽/视频分片码率。（$\mu$），输出速率为固定值 1 

当实际带宽大于请求码率， 缓冲区逐渐变大；当实际带宽小于请求码率， 缓冲区逐渐变小， 当缓冲区没有数据时， 无法继续进行播放，此时播放器进入二次缓冲（rebuffing）状态， 直到新的视频分片下载完毕后才能恢复正常播放  

由于避免上溢出现，造成带宽浪费，需要设置一个阈值max，详细数学模型在MPC节中。





## MPC

参数定义

$R_k$chunk K的码率

$d_k(R_k)$chunk的大小 constant的时候 ( $d_k(R_k)=L\times R_k$)，variable的时候是正比关系 $L$为chunk的长度

$q(.)$ 视频质量，函数是一个增函数，但具体函数和设备有关系

$B_k$开始接收第k个chunk的buffer size

$C_k$开始接收第k个chunk的平均throughput

### Buffer Dynamics model

$B_{k+1}=((B_k-\frac{d_k(R_k)}{C_k})_++L-\Delta t_k)$

就是当第k+1个chunk开始传的时候，此时的buffer size是 剩余的加上新增的

当 $B_k < \frac{d_k(R_k)}{C_k}$时

$\Delta t_k$是读完第k个chunk后需要等待的时间

$\Delta t_k=((B_k-\frac{d_k(R_k)}{C_k})_++L-B_{max})_+$

意思就是说，只有当buffer满的时候，$\Delta t_k$才会大于0.

### Definition of QoE

$QoE^K=\sum^K_{k=1} q(R_K)-\lambda\sum^{K-1}_{k=1} |q(R_{k+1}-q(R_k))-\mu \sum^K_{k=1} (\frac{d_k(R_k)}{C_k}-B_k)_+-\mu_s T_s$

可以看出来，QoE是四个factor的linear combination：质量，质量波动，卡住，启动时间



target：

$argmax_{R_k} QoR^K$

选择最优的$R_k$，使得QoE最大

选择的公式可数学化成

$R_k=f(B_k,{C_t,t>t_k},{R_i,i<k})$



## Robust MPC

$\max \min QoE$

先从所有的throughput里面选取最恶劣的情况，再最大化QoE。其实就是选取最小的throughput


import sys
import time
import gi
import queue

# Import cytypes to use libgstpcie library 
import ctypes
from ctypes import *

# LoadLibrary function is used to load the library into the process, and to get a handle to it.
libpath = '/usr/lib/libpciegst.so'
user32_dll = ctypes.cdll.LoadLibrary(libpath)

# global variable to store the pcie usecase data.
bytes_played = int(0)
class dma_buf_import(Structure):
    _fields_ = [("dbuf_fd", c_int),
                ("dma_imp_flag", c_uint),
                 ("dma_addr", c_int64),
               ("size",c_size_t),
               ("dir",c_char)]
class resolution_s(Structure):
    _fields_ = [("x", c_int),
                ("y", c_int)]

res_inp = resolution_s()
buf_queue = []    
gst_buffqueue = []

max_buffer = int(0)
usecase = c_int(0)
flength = c_uint64(0)
fps = c_int(0)
kernmode = c_int(0)
filtertype = c_int(0)

buff_fd_queue = queue.Queue(3)

memory_queue = queue.Queue(3)
max_buffers_count = int(3)

# pcie related control information provided from host machine
pcie_fd = user32_dll.pcie_open()
user32_dll.pcie_get_usecase_type(pcie_fd,byref(usecase))
user32_dll.pcie_get_file_length(pcie_fd,byref(flength))
user32_dll.pcie_get_fps(pcie_fd,byref(fps))
user32_dll.pcie_get_kernel_mode(pcie_fd,byref(kernmode))
user32_dll.pcie_get_filter_type(pcie_fd,byref(filtertype))
user32_dll.pcie_get_input_resolution(pcie_fd,byref(res_inp))
#src = Gst.ElementFactory.make("appsrc")
yuv_frame_size = res_inp.x * res_inp.y * 2  #YUY2_MULTIPLIER = 2

# Check required gst-python module versions 
gi.require_version('Gst', '1.0')
gi.require_version("GstApp", "1.0")
gi.require_version("GstAllocators", "1.0")

# Import required python modules
from gi.repository import GObject, GLib, Gst, GstApp
from gi.repository import GstAllocators

allocator = GstAllocators.DmaBufAllocator.new()

# Create an instance of struct to export dma-buf
class dma_buf(Structure):
	_fields_ = [("fd", c_int),
		("flags", c_uint),
		("size",c_size_t)]

duration = Gst.SECOND / (int(30))
dts = float(0)
frame_count = int(0)
dma_import = dma_buf_import()

# DMA Import callbacks for pciesink
def new_sample_cb(pcisink: GstApp.AppSink):
    sample = pcisink.pull_sample()
    buffer = sample.get_buffer()
    memory = buffer.peek_memory(0)
    fd = GstAllocators.dmabuf_memory_get_fd(memory)
    is_dma = GstAllocators.is_dmabuf_memory(memory)
    dma_import.dbuf_fd = fd
    ret = user32_dll.pcie_dma_import(pcie_fd,byref(dma_import))
    ret = user32_dll.pcie_write(pcie_fd ,yuv_frame_size, 0, 0)
    ret = user32_dll.pcie_dma_import_release(pcie_fd,byref(dma_import))
    return Gst.FlowReturn.OK

# DMA callbacks for python
def need_data(src: GstApp.AppSrc, length: int):
    #Created GST buffers
    gstbuffer = Gst.Buffer.new()
    # Added dma_buf structure instance to buffer object at runtime
    buffer = dma_buf()
    # Map exported dma buffer to an fd
    user32_dll.pcie_dma_map(pcie_fd,byref(buffer))
    buf_size = buffer.size
    #store exported dma buffer fd in a queue to get free fds
    buff_fd_queue.put(buffer.fd)
    # Initiate DMA Read transaction
    user32_dll.pcie_read(pcie_fd,yuv_frame_size)
    # Return a GstMemory that wraps a dmabuf file descriptor and provided doesnt close
    memory = GstAllocators.DmaBufAllocator.alloc_with_flags(allocator, buffer.fd,  buffer.size,GstAllocators.FdMemoryFlags.DONT_CLOSE)
    memory.size = buffer.size
    #Appends the memory block mem to buffer.
    gstbuffer.append_memory(memory)
    #Emit push-buffer signal to next element.
    retval = src.emit('push-buffer', gstbuffer)
    global bytes_played 
    global frame_count
    bytes_played += yuv_frame_size
    frame_count = frame_count + 1
    if(retval != Gst.FlowReturn.OK):
        print("Error while emitting buffer")
    if(bytes_played >= flength.value):
        print("playback is completed, Sending EOS")
        src.send_event(Gst.Event.new_eos())
    if( buff_fd_queue.qsize() >= max_buffers_count):
        #print("all bufer used, unmap last queued:{}".format(buff_fd_queue.qsize()))
        fd = int(buff_fd_queue.get())
        buffer = dma_buf()
        buffer.fd = fd
        buffer.size = buf_size#buf_size
    # Unap exported dma buffer fd    
    result = user32_dll.pcie_dma_unmap(pcie_fd,byref(buffer))

def xlnx_pciecleanup() :
        if(usecase.value != 1) :
                user32_dll.pcie_dma_export_release(pcie_fd,byref(dma_import))
        user32_dll.pcie_set_read_transfer_done(pcie_fd)
        user32_dll.pcie_set_write_transfer_done(pcie_fd)
        time.sleep(2)
        user32_dll.pcie_clr_write_transfer_done(pcie_fd)
        if(usecase.value != 1) :
            user32_dll.pcie_clr_read_transfer_done(pcie_fd)
        user32_dll.pcie_close()

class xlnx_pcieappsink :
	def __init__(self,sink : GstApp.AppSink) :
		self.sink = sink
		counter=0
		fmt = "YUY2"
		cap_string = "video/x-raw, width=" + str(3840) + ", height=" + str(2160) + ", format=" + fmt
		cap_string = cap_string + ", framerate=" + str(fps)+"/1"
		caps = Gst.ElementFactory.make("capsfilter")
		cap = Gst.Caps.from_string(cap_string)
		caps.set_property("caps", cap)
		self.sink.set_property("sync", False)
		self.sink.set_property("async", False)
		self.sink.set_property("emit-signals", True)
		self.sink.connect('new-sample', new_sample_cb)
		self.sink.set_property("caps",cap)

def xlnx_pcieappsrc (src, caps) :
		#self.src = src
		#self.caps = caps
    width = res_inp.x
    height = res_inp.y
    yuv_frame_size = width * height * 2
    fmt = "YUY2"
    cap_string = "video/x-raw, width=" + str(width) + ", height=" + str(height) + ", format=" + fmt
    cap_string = cap_string + ", framerate=" + str(fps.value)+"/1"
    cap = Gst.Caps.from_string(cap_string)
    caps.set_property("caps", cap)
    print(cap_string)
    src.set_property("format", Gst.Format.TIME)
    src.set_property("block", True)
    src.set_property("is-live", True)
    src.set_property("max-bytes", yuv_frame_size)
    src.set_property("caps",cap)
    src.set_property("stream-type",int(0))
    src.connect('need-data', need_data)

def PCIe_GetDevice() :
	return pcie_fd 

def PCIe_Getusecase(pcie_fd) :
	return usecase

def PCIe_GetResolution(pcie_fd) :
	return res_inp.y

def export_pciedmabuff(pcie_fd) :
    ndmabuf = 3 #Allocate 3 exported 3 dma buffer file descriptors
    export_fd_size = int(0)
    export_fd_size = user32_dll.get_export_fd_size(yuv_frame_size)
	#print(export_fd_size)	
    buffer_main = dma_buf()
    buffer_main.fd = 0
    buffer_main.size = export_fd_size
    user32_dll.pcie_num_dma_buf(pcie_fd,ndmabuf)
    user32_dll.pcie_dma_export(pcie_fd,byref(buffer_main))



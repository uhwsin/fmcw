import multiprocessing as mp
from fmcw import adc, ftdi
import time
import os

class fpga_reader(mp.Process):
    def __init__(self, connection, s):
        mp.Process.__init__(self)  # Calling super constructor - mandatory
        self.connection = connection
        self.s = s

        # Send some basic data back to the parent
        process_info = {
            'pid': os.getpid()
        }
        self.connection.send(process_info)

    def run(self):
        self.adf4158 = adc.ADF4158()

        self.fpga = ftdi.FPGA(self.adf4158, encoding=self.s['encoding'])
        self.fpga.set_gpio(led=True, adf_ce=True)
        self.fpga.set_adc(oe2=True)
        self.fpga.clear_adc(oe1=True, shdn1=True, shdn2=True)
        real_delay = self.fpga.set_sweep(self.s['f0'], self.s['bw'], self.s['t_sweep'], self.s['t_delay'])  # Returned value delay not used
        print("[INFO] Real delay between sweeps: {} s".format(real_delay))
        self.fpga.set_downsampler(enable=self.s['down_sampler'], quarter=self.s['quarter'])
        self.fpga.write_sweep_timer(self.s['t_sweep'])
        self.fpga.write_sweep_delay(self.s['t_delay'])
        self.fpga.write_decimate(self.s['acquisition_decimate'])
        self.fpga.write_pa_off_timer(self.s['t_delay'] - self.s['pa_off_advance'])
        self.fpga.clear_gpio(pa_off=True)
        self.fpga.clear_buffer()
        self.fpga.set_channels(a=self.s[1], b=self.s[2])  # Would not scale up

        # Run while nothing is put to the pipe - it is an "almost" read only pipe
        while True:
            self.connection.send_bytes(self.fpga.device.read(self.s['byte_usb_read']//self.s['sub_call']))

        # Close properly the fpga device
        self.fpga.set_adc(oe1=True, shdn1=True, shdn2=True)
        self.fpga.set_channels(a=False, b=False)
        self.fpga.clear_gpio(led=True, adf_ce=True)
        self.fpga.set_gpio(pa_off=True)
        self.fpga.clear_buffer()
        self.fpga.close()

        print("[INFO] FPGA subprocess successfully closed")
        return
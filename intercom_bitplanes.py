# Adding a buffer.

import sounddevice as sd
import numpy as np
import struct
from intercom_buffer import Intercom_buffer

if __debug__:
    import sys

class Intercom_bitplanes(Intercom_buffer):

    def init(self, args):
        Intercom_buffer.init(self, args)

    def run(self):

        self.recorded_chunk_number = 0
        self.played_chunk_number = 0
        self.bitplane_weight_1 = 0
        self.bitplane_weight_2 = 0

        def receive_and_buffer():
            message, source_address = self.receiving_sock.recvfrom(Intercom_buffer.MAX_MESSAGE_SIZE)
            chunk_number, *chunk = struct.unpack(self.packet_format, message)
            self._buffer[chunk_number % self.cells_in_buffer] = np.asarray(chunk).reshape(self.frames_per_chunk, self.number_of_channels)
            return chunk_number

        def record_send_and_play(indata, outdata, frames, time, status):
            message = struct.pack(self.packet_format, self.recorded_chunk_number, *(indata.flatten()))
            self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
            self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
            chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer].shape   
            #1 << 0   -- > 2^0 = 1.
            self.bitplane_weight_1 = chunk & 1
            #1 << 1  -- > 2^1 = 2. 
            #Temeos un chunk de 32 por lo que dividimos por 2. 
            self.bitplane_weight_2 = (chunk & (1 << 1)) >> 1

            print("Este es bitplane", self.bitplane_weigth_1)
            self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
            self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
            #outdata[:] = chunk
            outdata[:] = self.bitplane_weight_2
            if __debug__:
                sys.stderr.write("."); sys.stderr.flush()

        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=record_send_and_play):
            print("-=- Press CTRL + c to quit -=-")
            first_received_chunk_number = receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                receive_and_buffer()

if __name__ == "__main__":
    intercom = Intercom_bitplanes()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()

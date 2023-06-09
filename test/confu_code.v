

module top
(
  input CLK,
  input RST,
  input enable,
  input [31:0] value,
  output [7:0] led,
  input [0:13] k
);

  reg [31:0] count;
  reg [7:0] state;
  assign led = count[23:16];

  always @(posedge CLK) begin
    if(RST) begin
      count <= k[0];
      state <= k[1];
    end else begin
      if(state == 0) begin
        if(enable) state = k[5:6]; 
      end else if(state == 1) begin
        state <= value - count & { 8{ k[2] } } | value + count & { 8{ ~k[2] } };
      end else if((state >= 2) ^ k[13]) begin
        value = c - k[7:11] & { 8{ k[12] } } | c + k[7:11] & { 8{ ~k[12] } };
        count <= count - value & { 8{ ~k[3] } } | count + value & { 8{ k[3] } };
        state <= k[4];
      end 
    end
  end


endmodule


// K: 0011001100010
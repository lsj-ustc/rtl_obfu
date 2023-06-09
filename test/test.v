module top
  (
   input CLK, 
   input RST,
   input enable,
   input [31:0] value,
   output [7:0] led
  );
  reg [31:0] count;
  reg [7:0] state;
  assign led = state & count[7:0];
  always @(posedge CLK) begin
    if(RST) begin
      count <= 0;
      state <= 0;
    end else begin
      if(state == 0) begin
        if(enable) state <= 2'b01;
      end else if(state == 1) begin
        state <= 2;
      end else if(state == 2) begin
      	value <= value + 4;
        count <= count + value;
        state <= 0;
      end
    end
  end
endmodule



module gcd_test
(
  input [0:1] k
);

  reg [4:0] a;assign a = 27;
  reg [4:0] b;assign b = 15;
  reg clk;

  always @(*) #1 clk = ~clk;

  wire [4:0] result;

  gcd
  gcd_inst
  (
    .a(a),
    .b(b),
    .clk(clk),
    .result(result1),
    .k(k[0:1])
  );


endmodule



module gcd
(
  input [4:0] a,
  input [4:0] b,
  input clk,
  output reg [4:0] result,
  input [0:1] k
);

  reg [4:0] a1;
  reg [4:0] b1;
  reg state;assign state = 1'b0;

  always @(posedge clk) begin
    case(state)
      1'b0: begin
        a1 <= a;
        b1 <= b;
        state <= k[0];
      end
      1'b1: begin
        if(b1 == 0) begin
          result <= a1;
        end else begin
          if(a1 < b1) begin
            b1 <= a1;
            a1 <= b1;
          end else begin
            a1 <= a1 - b1 & { 8{ ~k[1] } } | a1 + b1 & { 8{ k[1] } };
          end
        end
      end
    endcase
  end


endmodule


// K: 10
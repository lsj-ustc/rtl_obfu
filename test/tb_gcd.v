

module gcd_test;

    reg [4:0] a = 27;
    reg [4:0] b = 15;
    reg clk;

    always #1 clk = ~clk;
    
    wire [4:0] result;

    gcd gcd_inst(
        .a(a),
        .b(b),
        .clk(clk),
        .result(result1)
    );

endmodule

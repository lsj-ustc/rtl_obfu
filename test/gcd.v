module gcd (
    input [4:0] a,
    input [4:0] b,
    input clk,
    output reg [4:0] result
);

reg [4:0] a1;
reg [4:0] b1;

reg state = 1'b0;

always @(posedge clk) begin
    case(state)
    1'b0:begin
        a1 <= a;
        b1 <= b;
        state <= 1'b1;
    end

    1'b1:begin
        if (b1 == 0) begin
            result <= a1;
        end else begin
            if(a1 < b1) begin
                b1 <= a1;
                a1 <= b1;
            end else begin
                a1 <= a1 - b1;
            end
        end
    end
    endcase
end

endmodule
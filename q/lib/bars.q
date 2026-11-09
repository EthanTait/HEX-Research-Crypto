/ query functions research calls. tbl is a table name: `l1bar, `tradebar or `bookbar

/ long rows as stored, for file dates d0..d1. always returns date, sym, ts_end, carryover plus c
/ date is first in the where clause so only those partitions are opened; sym second uses p#
bars:{[tbl;syms;d0;d1;c]
  c:distinct `date`sym`ts_end`carryover,c;
  ?[tbl;((within;`date;(d0;d1));(in;`sym;enlist (),syms));0b;c!c]}

/ the data-chapter table: per sym and file-date year. must match output/coverage/by_year.csv
/ two steps: count inside each (date, sym) on disk, then add up the small result in memory
coverage:{[tbl;d0;d1]
  t:select bars:count i, co_ge1:sum carryover>=1, co_m1:sum carryover=-1 by date, sym from tbl where date within (d0;d1);
  select days:count i, bars:sum bars, co_ge1:sum co_ge1, co_m1:sum co_m1 by sym, year:`year$date from t}

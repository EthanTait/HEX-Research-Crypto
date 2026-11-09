/ raw .csv.gz -> date-partitioned hdb. run from the repo root: q q/load/bars.q
\l q/lib/cfg.q
\l q/schema/bars.q

/ epoch ms -> q timestamp. the files count ms from 1970, q counts ns from 2000
ms2ts:{1970.01.01D00:00:00.000000000+1000000*`long$x}

/ the 5 expected files for one table and one file date, and whether each exists
files:{[tbl;d]
  ymd:string[d] except ".";
  dir:.cfg.paths[`raw_fordham],"/binance/futures/latest/",string[.schema.ds tbl],"/",ymd,"/";
  p:{[dir;ymd;suf;s] dir,string[s],".",ymd,".",suf,".1min.csv.gz"}[dir;ymd;string .schema.suf tbl] each .schema.syms;
  ([] sym:.schema.syms; path:p; ok:{not ()~key hsym `$x} each p)}

/ one file -> typed table with the course column names. no sym or date yet
readFile:{[tbl;path]
  t:(.schema.types tbl;enlist ",") 0: system "zcat ",path;
  if[not cols[t]~.schema.cols tbl; '"header mismatch: ",path];
  if[1440<>count t; '"not 1440 rows: ",path];
  t:update ts_end:ms2ts ts_end from t;
  if[tbl=`bookbar; t:update ts_book:ms2ts ts_book from t];
  if[any null t`ts_end; '"null ts_end: ",path];
  t}

/ one file date -> one partition. .Q.dpft enumerates sym, sorts by sym, sets p#, writes splayed
writeDay:{[tbl;d]
  f:select from files[tbl;d] where ok;
  if[0=count f; -1 "no files: ",string[tbl]," ",string d; :()];
  t:raze {[tbl;s;p] `sym xcols update sym:s from readFile[tbl;p]}[tbl]'[f`sym;f`path];
  tbl set t;
  .Q.dpft[hsym `$.cfg.paths`hdb;d;`sym;tbl];
  update date:d from 0!select rows:count i by sym from t}

/ every file date in d0..d1. a bad date is reported and skipped, not fatal
loadAll:{[tbl;d0;d1]
  raze {[tbl;d] @[writeDay[tbl];d;{[d;e] -2 "FAILED ",string[d],": ",e; ()}[d]]}[tbl] each d0+til 1+d1-d0}

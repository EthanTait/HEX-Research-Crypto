/ entry point for the ide and pykx. start from the repo root: q q/init.q
\l q/lib/cfg.q
\l q/schema/bars.q
\l q/lib/bars.q
/ mount last: loading a directory also moves q into it
system "l ",.cfg.paths`hdb

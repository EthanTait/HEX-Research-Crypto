/ have to start q from repo root
.cfg.root:first system "pwd"

/ keep the indented "key: value" lines of local.yaml, split on ": ", make relative paths abs
.cfg.read:{
  l:read0 hsym `$.cfg.root,"/config/local.yaml";
  kv:": " vs/: trim each l where l like " *";
  kv:kv where 2=count each kv;
  v:{$["/"=first x; x; .cfg.root,"/",x]} each kv[;1];
  (`$kv[;0])!v}

.cfg.paths:.cfg.read[]

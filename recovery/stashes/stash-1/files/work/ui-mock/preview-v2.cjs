const http=require('node:http');
const fs=require('node:fs');
http.createServer((req,res)=>{
  const url=new URL(req.url,'http://127.0.0.1:5188');
  if(url.pathname!=='/'){res.writeHead(404);res.end();return;}
  const scenario=['ready','stale','empty','error','partial'].includes(url.searchParams.get('scenario'))?url.searchParams.get('scenario'):'ready';
  const dark=url.searchParams.get('theme')==='dark';
  res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});
  res.end('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cultiva — revisión del mock</title><style>:root{color-scheme:'+ (dark?'dark':'light')+'}body{margin:0;padding:16px;background:'+ (dark?'#121a16':'#e7ebe4')+'}main{max-width:1024px;margin:auto}button,summary{cursor:pointer}#qa{max-width:1024px;margin:0 auto 8px;font:12px system-ui;color:'+(dark?'#dedede':'#444')+'}</style><div id="qa">Vista aislada de revisión · No conectada a la aplicación</div><script>window.openai={widgetState:{privateContent:{scenario:'+JSON.stringify(scenario)+'}},setWidgetState:()=>Promise.resolve()};</script><main>'+fs.readFileSync(__dirname+'/cultivo-claro-v2.html','utf8')+'</main></html>');
}).listen(5188,'127.0.0.1',()=>console.log('Mock disponible en http://127.0.0.1:5188'));

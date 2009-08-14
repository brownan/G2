var s1;
function listenswf() {
  if (s1 == undefined) {
    s1 = new SWFObject("images/flvplayer.swf","playlist","95","20","7");
    s1.addVariable("autostart","true");
    s1.addVariable("file","images/g2.xml");
    s1.write("player");
  } else {
    document.getElementById('player').innerHTML = "";
    s1 = undefined;
  }
}
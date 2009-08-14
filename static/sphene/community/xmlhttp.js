    function getHttpObject() {
      // TODO - move this method into an external .js file !!
      var xmlhttp;
      /*@cc_on
        @if (@_jscript_version >= 5)
          try { xmlhttp = new ActiveXObject("Msxml2.XMLHTTP");
          } catch(e) {
            try { xmlhttp = new ActiveXObject("Microsoft.XMLHTTP");
            } catch (E) { xmlhttp = false; }
          }
        @else
          xmlhttp = false;
        @end
      @*/
      if (!xmlhttp && typeof XMLHttpRequest != 'undefined') { try { xmlhttp = new XMLHttpRequest(); } catch (e) { xmlhttp = false; } }
      return xmlhttp;
   }


   function showResponseInElement(elementId, loadText, url) {
     var previewarea = document.getElementById(elementId);
     previewarea.style.display = "block";
     previewarea.style.visibility = "visible";
     previewarea.innerHTML = loadText;

     var http = getHttpObject();
     http.onreadystatechange = function() {
       if(http.readyState == 4) {
         if(http.status == 200) {
           previewarea.innerHTML = http.responseText;
         }
       }
     };
     http.open("POST",".");
     http.send( url );
   }
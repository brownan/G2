jQuery(document).ready(function(){
        $(".sphblockregion").sortable( { 
                connectWith: jQuery('.sphblockregion').get(), 
                placeholder: 'sphblockregion_placeholder',
                update: function(e,ui) {
                    //window.defaultStatus = 'Saving new positions ...';
                    var oldtitle = document.title;
                    document.title = oldtitle + '  Storing new positions ...';
                    var request = '';
                    var regions = '';
                    $(".sphblockregion").each(function(){
                            var block_region = this.getAttribute( 'sphblock_region' );
                            //alert('testing' + $(this).sortable('serialize'));
                            request += block_region + '=' + encodeURIComponent($(this).sortable('serialize')) + '&';
                            regions += 'block_region=' + block_region + '&';
                        });
                    //alert("all serialized: " + test);
                    //alert( 'request: ' + request + regions );
                    jQuery.ajax({
                            type: 'POST',
                            url: sphblockframework_sorturl, 
                            data: request + regions,
                            success:function (data, status) {
                                document.title = oldtitle;
                            },
                            error:function (req, status, error) {
                                //$("#content").html(status);
                                document.title = oldtitle;
                            }});
                    //alert( 'updated ' + $(this).sortable('serialize') );
                },
                start: function(e,ui) {
                    $(this).css('z-index', 5);
                    $(ui.helper[0]).css('z-index', 8);
                    $(ui.helper[0]).css('border', '1px solid black');
                    $(".sphblockregion").addClass( 'whilesorting' )
                },
                stop: function(e,ui) {
                    $(".sphblockregion").removeClass( 'whilesorting' )
                },
                zIndex: 1001,
                    } );
    });

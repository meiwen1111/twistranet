// Share/Like js helpers

jq(function()
{
  jq(".i_like,.i_unlike,.toggle_like").live('click', function(e)
  {
    if (jq(e.target).is( "a" )) obj = jq(this).parent();
    else obj =this;
    e.preventDefault();
    var ID = jq(obj).attr("id").replace('toggle_like_','');
    jq.ajax({
      type: "GET",
      url: home_url + "share/like_toggle_by_id/" + ID,
      cache: false,
      success: function(data){
        jq(jq(obj).parent()).html(data);
      }
    });
    return false;
  });
  jq('.n_likes').live('mouseenter', function(){
    jq('>.f_likes', jq(this).parent()).css('display', 'block');
  });
  jq('.f_likes').live('mouseleave', function(){
    jq(this).css('display', 'none');
  });
});

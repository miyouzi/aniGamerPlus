layui.use('element', function(){
	let element = layui.element;
	
	let protocol = window.location.protocol;
	let ws = protocol.replace('http', 'ws');
	let tasks_progress_url = ws+'//'+window.location.host+'/data/tasks_progress'+'?token=';
	
	// 获取token
	$.get('data/get_token', function(token){
		tasks_progress_url += token;
		
		let ws = new WebSocket(tasks_progress_url);
		ws.onmessage = function(evt){
			let data = $.parseJSON(evt.data);
			if (Object.keys(data).length == 0){
				$('#no_task').show();
			} else {
				$('#no_task').hide();
				for (let sn in data){
					
					if ($('#'+sn).length > 0) {
						// 如果该任务卡片已存在
						$("#status"+sn).html(data[sn]["status"]);
						$("#header"+sn).html(data[sn]["filename"]);						
						element.progress(sn, Math.round(data[sn]["rate"])+'%');
					} else {
						// 如果该任务卡片不存在
						let task_item_templates = `
							<div class="layui-col-xs12 layui-card" id=${sn}>
								<div class="layui-card-header" style="height:auto !important;" id=${"header"+sn}>${data[sn]["filename"]}</div>
								<div class="layui-card-body layui-row">
									<div class="layui-col-xs3" style="text-align: center;" id=${"status"+sn}>${data[sn]["status"]}</div>
									<div class="layui-col-xs9" style="padding: 3px;">
										<div class="layui-progress layui-progress-big" lay-showpercent="true" lay-filter=${sn}>
											<div class="layui-progress-bar" lay-percent="0%">
												<span class="layui-progress-text">0%</span>
											</div>
										</div>
									</div>
								</div>
							</div>
						`;
						$("#task_info_panel").prepend(task_item_templates);
						element.progress();
					}
				}
			}
		}
		
	});
});

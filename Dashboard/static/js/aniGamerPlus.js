var dataArrays; //用户配置json
var proxy_protocol;
var proxy_ip;
var proxy_port;
var proxy_user = '';
var proxy_passwd = '';
id_list.push('proxy_protocol', 'proxy_ip', 'proxy_port', 'proxy_user', 'proxy_passwd');

$.ajax({
	type: "get",
	url: "data/config.json",
	dataType: "json",
	async: true,
	success: function(data) {
		dataArrays = data;
		parseProxy(data.proxy);
		$(function (){
			renderJson();
		});
	}
});

showSnList();

function parseProxy(proxy) {
	proxy_protocol = proxy.replace(/:\/\/.*/i, '').toUpperCase();
	if (/.*@.*/.test(proxy)) {
		proxy_user = /:\/\/.*?:/g.exec(proxy)[0].replace(/:(\/\/)?/g, '');
		proxy_passwd = /:.*@/.exec(proxy)[0].replace(proxy_user, '')
			.replace(/(:\/\/:)?@?/g, '');
		proxy = proxy.replace(proxy_user + ':' + proxy_passwd + '@', '');
	}
	var tmp = proxy.replace(/.*:\/\//i, '');
	if (proxy.length > 0) {
		proxy_ip = /:.*:/.exec(proxy)[0].replace(/:(\/\/)?/g, '');
		proxy_port = /:\d+/.exec(proxy)[0].replace(/:/, '');
	} else {
		proxy_ip = '';
		proxy_port = '';
	}
	
	dataArrays.proxy_protocol = proxy_protocol;
	dataArrays.proxy_ip = proxy_ip;
	dataArrays.proxy_port = proxy_port;
	dataArrays.proxy_user = proxy_user;
	dataArrays.proxy_passwd = proxy_passwd;
}

function reloadSetting() {
	readJson();
	renderJson();
}

function readJson() {
	$.getJSON("data/config.json", function(data) {
		dataArrays = data;
		parseProxy(data.proxy); // 解析代理配置
	});
}

function renderJson() {
	for (var id of id_list) {
		if (id == 'proxy') continue; //代理设置已被分解
		var idType = document.getElementById(id).type;
		switch (idType) {
			case 'text':
			case 'number':
			case 'password':
				if (id  == 'multi-thread')  // 手动任务的默认线程数
					$('#manual_thread_limit').val(dataArrays[id]);
				$("#" + id).val(dataArrays[id]);
				break;
			case 'checkbox':
				$("#" + id).bootstrapSwitch('state', dataArrays[id]);
				break;
			case 'select-one':
				if (id == 'proxy_protocol') {
					$("#" + id).selectpicker('val', dataArrays[id].toUpperCase());
				} else {
					$("#" + id).find("option:contains('" + dataArrays[id] + "')")
						.prop("selected", true);
					$("#" + id).selectpicker('render');
				}
				break;

		}
	}
}


function readSettings() {
	for (var id of id_list) {
		if (id == 'proxy') continue; //代理设置已被分解

		var idType = document.getElementById(id).type;
		switch (idType) {
			case 'number':
				dataArrays[id] = Number($("#" + id).val());
				break;
			case 'text':
			case 'password':
				dataArrays[id] = $("#" + id).val();
				break;
			case 'checkbox':
				dataArrays[id] = $("#" + id).is(":checked");
				break;
			case 'select-one':
				if (id == 'proxy_protocol') {
					dataArrays[id] = $("#proxy_protocol").val().toLowerCase();
				} else if (id == 'download_resolution') {
					dataArrays[id] = $("#download_resolution").val().replace('P', '');
				} else {
					dataArrays[id] = $("#" + id).val();
				}
				break;
		}

		// 合并代理配置
		var a = ['proxy_protocol', 'proxy_ip', 'proxy_port', 'proxy_user', 'proxy_passwd'];
		for (var i in a) {
			var ip_port = dataArrays["proxy_ip"] + ':' + dataArrays["proxy_port"];
			var protocol = dataArrays["proxy_protocol"] + '://';
			if (dataArrays["proxy_user"]?.length * dataArrays["proxy_passwd"]?.length == 0) {
				// 如果没有用户密码
				dataArrays["proxy"] = protocol + ip_port;
			} else {
				// 如果有用户密码
				var user_pw = dataArrays["proxy_user"] + ':' + dataArrays["proxy_passwd"] + '@';
				dataArrays["proxy"] = protocol + user_pw + ip_port;
			}

		}
	}

	$.ajax({
		url: '/uploadConfig',
		type: 'post',
		dataType: 'json',
		headers: {
			"Content-Type": "application/json;charset=utf-8"
		},
		contentType: 'application/json; charset=utf-8',
		data: JSON.stringify(dataArrays),
		success: function(data) {
			// 向用户提示提交成功
			$('#uploadOk').show();
			$('#uploadFailed').hide();
			$('#uploadStatus').modal();
			reloadSetting();
		},
		error:function(status){
			// 向用户提示提交失败
			$('#uploadOk').hide();
			$('#uploadFailed').show();
			$('#uploadStatus').modal();
		}
	})
}

function getUA(){
	$('#ua').val(navigator.userAgent);
	alert("已取得當前瀏覽器UA");
}

function readManualConfig(){
	var manualData = {};
	var link = $('#manual_link').val();
	if (link.length == 0) {
		alert('請輸入影片鏈接！')
	} else {
		var sn = link.replace(/(https:\/\/)?ani\.gamer\.com\.tw\/animeVideo\.php\?sn=/i, '');
		manualData['sn'] = sn;
		
		var mode = $("#manual_mode").val();
		manualData['mode'] = mode;
		
		var resolution = $('#manual_resolution').val().replace('P', '');
		manualData['resolution'] = resolution;
		
		var classify = $('#manual_classify').is(":checked");
		manualData['classify'] = classify;
		
		var thread = $('#manual_thread_limit').val();
		manualData['thread'] = thread;

		var danmu = $('#manual_danmu').is(":checked");
		manualData['danmu'] = danmu;
		
		$.ajax({
			url: '/manualTask',
			type: 'post',
			dataType: 'json',
			headers: {
				"Content-Type": "application/json;charset=utf-8"
			},
			contentType: 'application/json; charset=utf-8',
			data: JSON.stringify(manualData),
			success: function(data) {
				// 向用户提示提交成功
				$('#uploadOk').show();
				$('#uploadFailed').hide();
				$('#uploadStatus').modal();
				reloadSetting();
			},
			error:function(status){
				// 向用户提示提交失败
				$('#uploadOk').hide();
				$('#uploadFailed').show();
				$('#uploadStatus').modal();
			}
		})
	}
	
}

function postSnList(){
	var sn_list = $('#sn_list').val();
	
	$.ajax({
		url: '/sn_list',
		type: 'post',
		dataType: 'text',
		headers: {
			"Content-Type": "text/plain; charset=utf-8"
		},
		contentType: 'text/plain; charset=utf-8',
		data: sn_list,
		success: function(data) {
			// 向用户提示提交成功
			$('#uploadOk').show();
			$('#uploadFailed').hide();
			$('#uploadStatus').modal();
			showSnList();
		},
		error:function(status){
			// 向用户提示提交失败
			$('#uploadOk').hide();
			$('#uploadFailed').show();
			$('#uploadStatus').modal();
		}
	})
}

function showSnList(){
	$.get("data/sn_list", function(data) {
		$("#sn_list").val(data);
	})
}
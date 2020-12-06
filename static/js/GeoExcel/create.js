$(document).ready(function(){
    var remainCol = {};
    for(var i = 0; i < columns.length; i++)
    {
        remainCol[columns[i]]=true;
    }
    remainCol['coord']=false;
    window.Col = remainCol;

    $('#button1step').click(function(){
        var val = $('select.table1Long').children("option:selected").val();
        var val1 = $('select.table1Lat').children("option:selected").val();
        if((val != 'None' && val1 != 'None') || (val == 'None' && val1 == 'None')){
            $('#button1step').hide();
            $('#2Step').show();
        }
    });

    $('#button2step').click(function(){
        $('#button2step').hide();
        var select_value = $('#table2primaryKey').children("option:selected").val();
        if (select_value == 'coord')
            alert("Be careful. If coord is a primary key, there will be a error to render the layer.")
        $('#3Step').show();
        searchTables(searchtablefor3Step);
    });

    $('#button3step').click(function(){
        $('#button3step').hide();
        $('#4Step').show();
        $('#submit').show();
    });

    $('#newEntries').click(function(){
        searchTables(searchtablefor3Step);
    });

    $('#deleteEntries').click(function(){
        var count = document.getElementById('table3').rows.length;
        if( count > 1){
            document.getElementById('table3').rows[count - 1].remove();
        }
    });

    $("select.table1Long").change(function(){
        var oldvalue = $.data(this, 'table1Long');
        change1stStep(this, 'select.table1Lat',oldvalue);
        $.data(this, 'table1Long',$(this).children("option:selected").val());    
    });

    $("select.table1Lat").change(function(){
        var oldvalue = $.data(this, 'table1Lat');
        change1stStep(this, 'select.table1Long',oldvalue);
        $.data(this, 'table1Lat',$(this).children("option:selected").val());       
    });

    $('#finalSubmit').click(function(){
        $("#foreignKeys").val($(".tableForeign").length);
    });
    
    $("#datum").select2();

    // $("#questionFile").change(function(){
    //     var val = $(this).children("option:selected").val();
    //     if(val == 'Yes')
    //     {
    //         $("#coor").hide();
    //         reset1Step();
    //         $("#foreignFile").show();
    //         searchTables(updateforeignFileTable);
    //     }
    //     else
    //     {
    //         resetForeignFileFields();
    //         $("#coor").show();
    //     }
    // });

        
    // $("#foreignFileTable").change(function(){
    //     var val = $(this).children("option:selected").val();
        
    //     var children = $("#foreignFileKey").children();

    //     for(var i = 0; i < children.length; i++)
    //     {
    //         if(children[i].value != 'None')
    //         {
    //             children[i].remove();
    //         }
    //     }
    //     if(val!= 'None')
    //     {
    //         searchTableKey(updateforeignFileKey,val,0);
    //     }
    // });

    // function updateforeignFileKey(success,resp,id)
    // {
    //     if(success)
    //     {
    //         for(i in resp.colname){
    //             $("#foreignFileKey").append(newOption(resp.colname[i]));
    //         }
    //     }
    // }

    // function updateforeignFileTable(success,resp)
    // {
    //     if(success)
    //     {
    //         for(i in resp.tables){
    //             $("#foreignFileTable").append(newOption(resp.tables[i]));
    //         }
    //     }
    // }
    
    // function reset1Step(){
    //     $("#table1Lat").val('None');
    //     $("#datum").val('None');
    //     $("#table1Long").val('None');
    //     $("#1stStepName").hide();
    // }

    // function resetForeignFileFields(){
    //     $("#foreignFile").hide();
    //     $("#foreignFileTable").val('None');
    //     $("#foreignFileKey").val('None');

    //     var aux = ["#foreignFileKey", "#foreignFileTable"];
    //     for(j in aux)
    //     {
    //         var children = $(aux[j]).children();
    
    //         for(var i = 0; i < children.length; i++)
    //         {
    //             if(children[i].value != 'None')
    //             {
    //                 children[i].remove();
    //             }
    //         }
    //     }
    // }

    function show4Step(value)
    {
        if(value != 'None' && value != undefined)
        {
            $("#table4"+ value +"").show();
        }
    };

    function hide4Step(value)
    {
        if(value != 'None' && value != undefined)
        {
            $("#table4"+ value).hide();
            $("#4Step"+value).val('None');
        }
    };

    function change1stStep(object, object1,oldvalue){
        var val = $(object).children("option:selected").val();
        var val1 = $(object1).children("option:selected").val();
        
        if(val == val1 && val != 'None')
        {
            alert("Be careful, you are selecting the same column in the 1st step");
            $(object).val('None');
        }
        else if(val != "None")
        {
            var children = $('#table2primaryKey').children();
            for(var i =0;i < children.length;i++)
            {
                if(children[i].value == val)
                {
                    children[i].remove();
                }
            }
            window.Col[val]=false;
        }
        
        if(oldvalue != undefined && oldvalue != 'None')
        {
            $('#table2primaryKey')
            .append(newOption(oldvalue));
            window.Col[oldvalue] = true;
        }
        
        if(val != 'None' && val1 != 'None'){
            if(val != val1)
            {
                $('#coord').show();
                window.Col['coord'] = true;
                $('#1stStepName').show();
            }
        }
        
        if(val == 'None'){
            $('#coord').hide();
            window.Col['coord'] = false;
            if ($('#table2primaryKey').children("option:selected").val() == 'coord'){
                $('#table2primaryKey').val('None');
            }
            $('#1stStepName').hide();
            $('#nameCoord').val('');
        }
        
        change3Step();
        hide4Step(val);
        show4Step(oldvalue);
    };

    function searchTables(afterSearch){
        $.ajax({
            url: path_search_tables,
            async: true,
            type: "GET",
            timeout: 600000, // sets timeout to 10 minutes
            error:function (jqXHR){
                console.log("error")
                afterSearch(false,jqXHR)
            },
            success: function(resp,status){
                if (resp.success){
                    afterSearch(true,resp)
                }
                else{
                    $('#info3step').show();
                }
            }
            
        });
    };

    function searchtablefor3Step(success,resp){
        if(success)
        {
            $('#info3step').hide();
            $('#error3step').hide();
            var count = document.getElementById('table3').rows.length;
            $('#table3').append(newRow(resp.tables));
            addListenersTo3step(count);
            checkAvailableColumns3Step(count);
        }
        else{
            $('#info3step').show();
            $("#error").remove();
            $("#error3step").append("<p id='error'> The problem is " + resp.responseJSON.error + "</p>");
            $("#error3step").show();
        }
    }


    function newRow(content){
        var html,i;
        var count = document.getElementById('table3').rows.length;
        html = "<tr><th><select name='column3Step"+ count +"' id = 'column3Step"+ count +"'>";
        html += "<option value='None'>None</option>";
        html += "<option id='column3Step"+ count +"_coord' value='coord'>coord</option>";
        for(i in columns){
            html += "<option id='column3Step"+ count +"_"+ columns[i]+ "' value='"+ columns[i] + "'>" + columns[i] + "</option>";
        }
        html += "</select></th><th><select name='tableForeign"+ count +"' class = 'tableForeign' id='tableForeign"+ count +"'>";
        html += "<option value='None'>None</option>";
        for(i in content){
            html += "<option value='"+ content[i] + "'>" + content[i] + "</option>";
        }
        html += "</select></th><th><select class = 'columnForeign' name='columnForeign"+count+"' id='columnForeign"+count+"' style='display: none;'>";
        html += "<option value='None'>None</option>";
        html += "</select></th><th><input type='hidden' id='dataType"+count+"' name='dataType"+count+"' value='None' /></th></tr>";
        
        return html;
    };

    function checkAvailableColumns3Step(id){
        for(name in window.Col){
            if(window.Col[name]){
                $("#column3Step"+id+"_"+name).show();
            }
            else{
                if($("#column3Step"+ id).children("option:selected").val() == name){
                    $("#column3Step"+ id).val('None');
                }
                $("#column3Step"+id+"_"+name).hide();
            }
        }

        var length = $(".tableForeign").length

        for(var i = 1 ; i <= length; i++)
        {
            if( i != id)
            {
                var val = $("#column3Step"+i).children("option:selected").val();
                if(val != 'None')
                    $("#column3Step"+id+"_"+val).hide();
            }
        }
    };

    function change3Step(){
        var length = $(".tableForeign").length

        for(var id = 1; id <= length; id ++)
        {
            checkAvailableColumns3Step(id);
        }
    };

    function addListenersTo3step(id)
    {
       
        $("#tableForeign"+id).change(function() {
            event.preventDefault();
            var val = $(this).children("option:selected").val();
            var id = this.id.split("tableForeign")[1];
            removeAllchilds(id);
            if(val!= 'None')
            {
                $("#columnForeign"+id).show();
                searchTableKey(searchtablekeyfor3Step,val,id);
            }
            else{
                $("#columnForeign"+id).hide();
                $('#info3step').hide();
                $("#error3step").hide();
            }
        });
    

        $("#columnForeign"+id).change(function() {
            event.preventDefault();
            var val = $(this).children("option:selected").val();
            var id = this.id.split("columnForeign")[1];
            if($("#column3Step"+id).children("option:selected").val() != 'None')
            {
                if(val!= 'None')
                {
                    $("#dataType"+id).val(dataTypeForeign[val]);
                }
                else{
                    $("#dataType"+id).val("None");
                }
            }
            else{
                $("#columnForeign"+id).val("None");
                $("#dataType"+id).val("None");
            }
        });

        $("#column3Step"+id).change(function(){
            event.preventDefault();
            var val = $(this).children("option:selected").val();
            var id = this.id.split("column3Step")[1];
            var oldvalue = $.data(this, 'table3');

            var length = $(".tableForeign").length

            for(var i = 1 ; i <= length; i++)
            {
                if( i != id)
                {
                    if($("#column3Step"+i).children("option:selected").val() == val)
                        $("#column3Step"+i).val('None')
                    $("#column3Step"+i+"_"+val).hide();
                    if(window.Col[oldvalue])
                        $("#column3Step"+i+"_"+oldvalue).show();
                }
            }

            hide4Step(val);
            show4Step(oldvalue);
            $.data(this, 'table3',val);


        });
    };

    function removeAllchilds(id)
    {
        console.log("Removing all childs from the foreign column")
        var children = $("#columnForeign"+id).children();

        for(var i = 0; i < children.length; i++)
        {
            if(children[i].value != 'None')
            {
                children[i].remove();
            }
        }

    };

    function searchTableKey(afterSearch,tableName, id)
    {
        $.ajax({
            url: path_search_tablekey,
            async: true,
            type: "GET",
            data:{
                'tableName':tableName
            },
            timeout: 600000, // sets timeout to 10 minutes
            error:function (jqXHR){
                console.log("error")
                afterSearch(false,jqXHR,id)
            },
            success: function(resp,status){
                console.log(resp)
                if (resp.success){
                    afterSearch(true,resp,id)
                }
                else{
                    $('#info3step').show();
                }
            }
            
        });

    };

    function searchtablekeyfor3Step(success,resp, id){
        if(success)
        {
            $('#info3step').hide();
            $("#error3step").hide();
            var dict = {};
            for(var i = 0; i < resp.colname.length; i++)
            {
                addNewOptions(id, resp.colname[i]);
                dict[resp.colname[i]]=resp.datatype[i];
            }
            window.dataTypeForeign = dict;
        }
        else{
            $('#info3step').show();
            $("#error").remove();
            $("#error3step").append("<p id='error'> The problem is " + resp.responseJSON.error + "</p>");
            $("#error3step").show();
        }
    }


    
    function addNewOptions(id,value)
    {
        $("#columnForeign"+id).append(newOption(value));
    };

    function newOption(value)
    {
        return $("<option></option>").attr("value",value).text(value);
    };

    
});



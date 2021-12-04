 <html lang="en"><head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <meta name="description" content="">
    <meta name="author" content="Mark Otto, Jacob Thornton, and Bootstrap contributors">
    <meta name="generator" content="Jekyll v4.0.1">
    <title>Group Info </title>

  
    <style>
      .bd-placeholder-img {
        font-size: 2rem;
        text-anchor: left;
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
      }

      body {
      padding-top: 90px;
    }

      @media (min-width: 768px) {
        .bd-placeholder-img-lg {
          font-size: 4.5rem;≤
        }
      }
    </style>
    <!-- Custom styles for this template -->
    <link href="/static/css/bootstrap.min.css" rel="stylesheet">

  </head>

  <%include file="header.mako" /> 
  <body>
  

<main role="main" class="container">

    <h1>Data Groups</h1>

  <div>
     <table id="series_table" class="table table-hover table-md table-responsive table-bordered table-striped" style="font-size: 0.8rem;">
            <thead>
              <tr>
                <th>Group name</th>
                <th>Fridge run</th>
                <th># series</th>
                <th># events</th>
                <th>Comments</th>
              </tr>
            </thead class="thead-dark">
            <tbody>
              % if len(grouplist) == 0:
                <tr class="table-danger">
                  <td colspan="10">
                    No groups found
                  </td>
                </tr>
              % endif
              % for s in grouplist:
                <tr id="groups_${s['group_name']}">
                  <td><a  href="/group/${s['group_name']}">${s['group_name']}</a></td>
                  <td>${s['fridge_run']}</td>
                  <td>${s['nb_series']}</td>
                  <td>${s['nb_events']}</td>
                  <td>${s['group_comment']}</td>
                </tr>
              % endfor
            </tbody>
          </table>
  </div>

</main><!-- /.container -->
<script src="https://code.jquery.com/jquery-3.5.1.slim.min.js" integrity="sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj" crossorigin="anonymous"></script>
<script>window.jQuery || document.write('<script src="/docs/4.4/assets/js/vendor/jquery.slim.min.js"><\/script>') </script> <script src="/static/js/bootstrap.bundle.min.js"></script>

</body></html>

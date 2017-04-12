<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:f="http://namespaces.zeit.de/functions" version="1.0">
    <xsl:output indent="yes" encoding="UTF-8" method="xml"/>
    <xsl:template name="convert_date"><xsl:param name="in"/><xsl:value-of select="substring($in,4,2)"/>.<xsl:value-of select="substring($in,1,2)"/>.<xsl:value-of
            select="substring($in,7,4)"/></xsl:template>
        <xsl:template name="convert_date_iso"><xsl:param name="in"/><xsl:value-of
            select="substring($in,7,4)"/>-<xsl:value-of select="substring($in,1,2)"/>-<xsl:value-of select="substring($in,4,2)"/>T06:00:00+00:00</xsl:template>

    <xsl:template match="EXPORT">
        <article>
            <xsl:apply-templates/>
        </article>
    </xsl:template>

    <!-- head -->

    <xsl:template match="HEADER">
        <head>
            <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="status">import</attribute>
            <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="ipad_template"><xsl:value-of select="substring-after(//iPad/@value,'_')" /></attribute>
            <attribute ns="http://namespaces.zeit.de/CMS/print" name="article_id"><xsl:value-of select="id/@value" /></attribute>

            <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="importsource">k4</attribute>
            <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="published">no</attribute><!-- noch zu klaren -->
            <attribute ns="http://namespaces.zeit.de/CMS/workflow" name="last-modified-by">import</attribute>
            <attribute ns="http://namespaces.zeit.de/CMS/document" name="banner">yes</attribute>
            <attribute ns="http://namespaces.zeit.de/CMS/document" name="mostread">yes</attribute>
            <attribute ns="http://namespaces.zeit.de/CMS/document" name="type">article</attribute>
            <attribute ns="http://namespaces.zeit.de/CMS/document" name="comments">yes</attribute>
            <attribute ns="http://namespaces.zeit.de/CMS/document" name="paragraphsperpage">7</attribute>
            <attribute ns="http://namespaces.zeit.de/CMS/document" name="show_commentthread">yes</attribute>
            <attribute ns="http://namespaces.zeit.de/CMS/document" name="in_rankings">yes</attribute>

            <xsl:apply-templates/>
            <xsl:apply-templates select="/EXPORT/IMAGE" />
            <xsl:apply-templates mode="ressort"/>
        </head>
    </xsl:template>

    <!-- convert stupid metadata-format -->

    <xsl:template match="HEADER/Autor">
        <attribute ns="http://namespaces.zeit.de/CMS/document" name="author">
            <xsl:value-of select="@value"/>
        </attribute>
    </xsl:template>

    <xsl:template match="/EXPORT/IMAGE">
        <zon-image>
            <xsl:attribute name="vivi_name">
                <xsl:value-of select="concat('img-', position())" />
            </xsl:attribute>
            <xsl:attribute name="k4_id">
                <xsl:value-of select="@path" />
            </xsl:attribute>
        </zon-image>
    </xsl:template>

    <xsl:template match="Frames">
        <xsl:copy-of select="." />
    </xsl:template>

    <xsl:template match="Frames" mode="ressort" />

    <xsl:template match="HEADER/Ressort" mode="ressort">
        <xsl:variable name="ressort">
            <xsl:choose>
                <xsl:when test="@value='Reise'">Reisen</xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="@value"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:variable name="map-doc" select="document($ressortmap_url)//mapping[@id=$ressort]" />
        <xsl:choose>
            <xsl:when test="$map-doc !=''">
                <attribute ns="http://namespaces.zeit.de/CMS/document" name="ressort">
                    <xsl:value-of select="$map-doc/online_ressort"/>
                </attribute>
                <xsl:if test="$map-doc/online_sub_ressort != ''">
                    <attribute ns="http://namespaces.zeit.de/CMS/document" name="sub_ressort">
                        <xsl:value-of select="$map-doc/online_sub_ressort"/>
                    </attribute>
                </xsl:if>
                <attribute ns="http://namespaces.zeit.de/CMS/print" name="ressort">
                    <xsl:value-of select="$map-doc/print_ressort"/>
                </attribute>
            </xsl:when>
            <xsl:otherwise>
                <attribute ns="http://namespaces.zeit.de/CMS/print" name="ressort"><xsl:value-of select="$ressort" /></attribute>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="HEADER/Zugang">
        <attribute ns="http://namespaces.zeit.de/CMS/document" name="access">
            <xsl:value-of select="f:map_access(@value)" />
        </attribute>
    </xsl:template>

    <xsl:template match="HEADER/PublicationID">
        <attribute ns="http://namespaces.zeit.de/CMS/print" name="publication-id">
            <xsl:value-of select="@value"/>
        </attribute>
    </xsl:template>

    <xsl:template match="HEADER/name">
        <attribute ns="http://namespaces.zeit.de/CMS/document" name="jobname">
            <xsl:value-of select="@value"/>
        </attribute>
        <attribute ns="http://namespaces.zeit.de/CMS/document" name="origname">
            <xsl:value-of select="@value"/>
        </attribute>
    </xsl:template>

    <xsl:template match="HEADER/Seite-von">
        <attribute ns="http://namespaces.zeit.de/CMS/document" name="page">
            <xsl:value-of select="@value"/><xsl:if test="//HEADER/Seite-bis/@value != ''">-<xsl:value-of select="//HEADER/Seite-bis/@value"/></xsl:if>
        </attribute>
        <!--attribute ns="http://namespaces.zeit.de/QPS/attributes" name="page">
            <xsl:value-of select="@value"/>
        </attribute-->
    </xsl:template>

    <xsl:template match="HEADER/Ausgabe">
        <attribute ns="http://namespaces.zeit.de/CMS/document" name="volume">
            <xsl:value-of select="substring-before(@value,'/')"/>
        </attribute>
        <!--attribute ns="http://namespaces.zeit.de/QPS/attributes" name="volume">
            <xsl:value-of select="substring-before(@value,'/')"/>
        </attribute-->
        <attribute ns="http://namespaces.zeit.de/CMS/document" name="year">20<xsl:value-of select="substring-after(@value,'/')"/></attribute>
    </xsl:template>

    <xsl:template match="HEADER/Erscheinungsdatum">
        <attribute ns="http://namespaces.zeit.de/CMS/document" name="erscheint">
            <xsl:call-template name="convert_date">
                <xsl:with-param name="in" select="@value"/>
            </xsl:call-template>
        </attribute>

                <attribute ns="http://namespaces.zeit.de/CMS/document" name="date_first_released">
                        <xsl:call-template name="convert_date_iso">
                                <xsl:with-param name="in" select="@value"/>
                        </xsl:call-template>
                </attribute>

        <attribute ns="http://namespaces.zeit.de/CMS/document" name="copyrights">DIE ZEIT, <xsl:call-template name="convert_date">
                <xsl:with-param name="in" select="@value"/>
            </xsl:call-template> Nr. <xsl:value-of select="substring-before(/EXPORT/HEADER/Ausgabe/@value,'/')"/>
        </attribute>
    </xsl:template>

    <!-- body -->
    <xsl:template match="STORY">
        <body>
            <xsl:apply-templates select="p" mode="supertitle"/>
            <xsl:apply-templates select="p" mode="title"/>
            <xsl:apply-templates select="p" mode="subtitle"/>
            <xsl:apply-templates select="p" mode="blocker"/>
            <xsl:apply-templates select="p" mode="bu"/>
            <xsl:apply-templates />
            <xsl:apply-templates select="p" mode="bib-title"/>
            <xsl:apply-templates select="p" mode="bib-info"/>
        </body>
    </xsl:template>

    <xsl:template match="p" mode="supertitle">
        <xsl:if test="contains(@pstyle, 'Dachzeile')">
                <supertitle>
                    <xsl:apply-templates/>
                </supertitle>
        </xsl:if>
    </xsl:template>

    <xsl:template match="p" mode="title">
        <xsl:if test="contains(@pstyle, 'berschrift')">
                <title>
                    <xsl:apply-templates/>
                </title>
        </xsl:if>
    </xsl:template>

    <xsl:template match="p" mode="subtitle">
        <xsl:if test="contains(@pstyle, 'Unterzeile')">
                <subtitle>
                    <xsl:apply-templates/>
                </subtitle>
        </xsl:if>
    </xsl:template>

    <xsl:template match="p" mode="blocker">
        <xsl:if test="contains(@pstyle,'Blocker')">
                <blocker>
                    <xsl:apply-templates/>
                </blocker>
        </xsl:if>
    </xsl:template>

    <xsl:template match="p" mode="bu">
        <xsl:if test="contains(@pstyle, 'BU')">
                <caption>
                    <xsl:apply-templates/>
                </caption>
        </xsl:if>
    </xsl:template>

    <xsl:template match="p" mode="bib-title">
        <xsl:if test="contains(@pstyle, 'Bibliografie+Kleintexte fett')">
                <bibliografie-title>
                    <xsl:apply-templates/>
                </bibliografie-title>
        </xsl:if>
    </xsl:template>

    <xsl:template match="p" mode="bib-info">
        <xsl:if test="contains(@pstyle, 'Bibliografie+Kleintexte normal')">
                <bibliografie-info>
                    <xsl:apply-templates/>
                </bibliografie-info>
        </xsl:if>
    </xsl:template>

    <xsl:template match="p">
        <xsl:choose>
            <xsl:when test="contains(@pstyle, 'berschrift')" />
            <xsl:when test="contains(@pstyle, 'Unterzeile')" />
            <xsl:when test="contains(@pstyle, 'Zwischentitel')">
                <intertitle>
                    <xsl:apply-templates/>
                </intertitle>
            </xsl:when>
            <xsl:when test="contains(@pstyle,'Bildnachweis')">
                <image-credits>
                    <xsl:apply-templates />
                </image-credits>
            </xsl:when>
            <xsl:when test="contains(@pstyle,'BU') or contains(@pstyle,'Blocker')"/>
            <xsl:when test="contains(@pstyle, 'Dachzeile')" />
            <xsl:when test="contains(@pstyle, 'Bibliografie+Kleintexte fett')" />
            <xsl:when test="contains(@pstyle, 'Bibliografie+Kleintexte normal')" />
            <xsl:when test=".=''">
                <xsl:comment>empty</xsl:comment>
            </xsl:when>
            <xsl:otherwise>
                <p>
                         <xsl:apply-templates/>
                </p>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    <xsl:template match="span">
        <xsl:choose>

            <xsl:when test="@fface='VorspannExtraBold'">
                <em>
                    <xsl:apply-templates/>
                </em>
            </xsl:when>
            <xsl:when test="contains(@fface,'Bold')">
                <strong>
                    <xsl:apply-templates/>
                </strong>
            </xsl:when>
            <xsl:when test="contains(@fface,'Italic')">
                <em>
                    <xsl:apply-templates/>
                </em>
            </xsl:when>
            <xsl:otherwise>
                <!-- ignore it -->
                <xsl:apply-templates/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
</xsl:stylesheet>
